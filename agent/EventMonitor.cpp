#include "EventMonitor.h"

EventMonitor::EventMonitor(VideoRecorder& recorder, HttpClient& client) 
    : video_recorder(recorder), http_client(client), subscription(NULL), is_monitoring(false) {
}

std::string EventMonitor::LogEventDetails(EVT_HANDLE hEvent) {
    DWORD size = 0;
    DWORD used = 0;
    DWORD propertyCount = 0;
    json eventJson;

    EvtRender(NULL, hEvent, EvtRenderEventXml, size, NULL, &used, &propertyCount);
    if (ERROR_INSUFFICIENT_BUFFER == GetLastError()) {
        size = used;
        LPWSTR buffer = (LPWSTR)malloc(size);
        if (buffer) {
            if (EvtRender(NULL, hEvent, EvtRenderEventXml, size, buffer, &used, &propertyCount)) {
                // Convert wide string to narrow string using Windows API
                int bufferSize = WideCharToMultiByte(CP_UTF8, 0, buffer, -1, nullptr, 0, NULL, NULL);
                if (bufferSize > 0) {
                    std::string xmlStr(bufferSize, 0);
                    if (WideCharToMultiByte(CP_UTF8, 0, buffer, -1, &xmlStr[0], bufferSize, NULL, NULL)) {
                        // Remove null terminator if present
                        if (!xmlStr.empty() && xmlStr.back() == 0) {
                            xmlStr.pop_back();
                        }

                        // Parse XML
                        pugi::xml_document doc;
                        pugi::xml_parse_result result = doc.load_string(xmlStr.c_str());
                        
                        if (result) {
                            eventJson = XMLNodeToJson(doc.first_child());
                            Logger::Log(L"Event captured and parsed to JSON");
                        }
                    }
                }
            }
            free(buffer);
        }
    }

    return eventJson.dump(4);
}

// Helper function to convert XML nodes to JSON
json EventMonitor::XMLNodeToJson(const pugi::xml_node& node) {
    json result;

    // Handle attributes
    if (node.attributes_begin() != node.attributes_end()) {
        json attrs = json::object();
        for (const auto& attr : node.attributes()) {
            attrs[attr.name()] = attr.value();
        }
        result["@attributes"] = attrs;
    }

    // Handle child nodes
    bool has_children = false;
    for (const auto& child : node.children()) {
        has_children = true;
        auto childName = std::string(child.name());
        
        // Check if we have multiple nodes with the same name
        if (result.contains(childName)) {
            // If this is the first duplicate, convert to array
            if (!result[childName].is_array()) {
                json temp = result[childName];
                result[childName] = json::array();
                result[childName].push_back(temp);
            }
            result[childName].push_back(XMLNodeToJson(child));
        }
        else {
            result[childName] = XMLNodeToJson(child);
        }
    }

    // Handle text content
    if (!has_children && !node.text().empty()) {
        std::string text = node.text().get();
        // Try to parse as number if possible
        try {
            if (text.find('.') != std::string::npos) {
                result = std::stod(text);
            } else {
                result = std::stoll(text);
            }
        }
        catch (...) {
            // If parsing as number fails, store as string
            result = text;
        }
    }

    return result;
}

DWORD WINAPI EventMonitor::SubscriptionCallback(EVT_SUBSCRIBE_NOTIFY_ACTION action, PVOID pContext, EVT_HANDLE hEvent) {
    if (action == EvtSubscribeActionDeliver && pContext != NULL) {
        EventMonitor* monitor = static_cast<EventMonitor*>(pContext);
        auto now = std::chrono::system_clock::now();
        Logger::Log(L"Event detected at: " + Logger::GetCurrentTimestamp());
        
        // Log detailed event information
        std::string eventDetails = monitor->LogEventDetails(hEvent);
        std::cout << "\n\n\n\n\n JSON:" + eventDetails;

        std::unique_lock<std::mutex> lock(monitor->event_mutex);
        monitor->event_queue.push({now, eventDetails});
        monitor->event_cv.notify_one();
    }
    return ERROR_SUCCESS;
}
void EventMonitor::StartMonitoring() {
    Logger::Log(L"Starting event subscription thread");

    const auto& config = Configuration::getInstance().getConfig();
    std::wstring query = L"*[System[(EventID=" + 
                        std::to_wstring(config.event_monitor.event_id) + 
                        L")]]";

    Logger::Log(L"Monitoring channel: " + config.event_monitor.channel_path);
    Logger::Log(L"Using query: " + query);

    subscription = EvtSubscribe(
        NULL,                           // Session
        NULL,                           // SignalEvent
        config.event_monitor.channel_path.c_str(),
        query.c_str(),
        NULL,                           // Bookmark
        this,                           // Context
        (EVT_SUBSCRIBE_CALLBACK)SubscriptionCallback,
        EvtSubscribeToFutureEvents
    );

    if (NULL == subscription) {
        DWORD error = GetLastError();
        LPWSTR messageBuffer = nullptr;
        FormatMessageW(
            FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
            NULL, error, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
            (LPWSTR)&messageBuffer, 0, NULL
        );
        Logger::Log(L"EvtSubscribe failed with error " + std::to_wstring(error) + L": " + messageBuffer);
        LocalFree(messageBuffer);

        // Additional error checking and logging
        Logger::Log(L"Channel path length: " + std::to_wstring(config.event_monitor.channel_path.length()));
        Logger::Log(L"Query length: " + std::to_wstring(query.length()));

        // Try to verify channel exists
        EVT_HANDLE channelEnum = EvtOpenChannelEnum(NULL, 0);
        if (channelEnum) {
            DWORD dwBufferSize = 0;
            DWORD dwBufferUsed = 0;
            wchar_t* channelPath = NULL;
            Logger::Log(L"Available channels:");
            while (EvtNextChannelPath(channelEnum, dwBufferSize, channelPath, &dwBufferUsed)) {
                if (ERROR_INSUFFICIENT_BUFFER == GetLastError()) {
                    dwBufferSize = dwBufferUsed;
                    channelPath = (wchar_t*)realloc(channelPath, dwBufferSize * sizeof(wchar_t));
                    if (channelPath) {
                        if (EvtNextChannelPath(channelEnum, dwBufferSize, channelPath, &dwBufferUsed)) {
                            Logger::Log(std::wstring(channelPath));
                        }
                    }
                }
            }
            free(channelPath);
            EvtClose(channelEnum);
        }

        Logger::Log(L"Please ensure the channel exists and you have permission to access it.");
        Logger::Log(L"You may need to run this program as administrator.");
        return;
    }

    Logger::Log(L"Successfully subscribed to the channel.");
    Logger::Log(L"Monitoring for Event ID " + std::to_wstring(config.event_monitor.event_id));
    
    is_monitoring = true;

    // Start monitoring thread
    std::thread([this]() {
        while (is_monitoring) {
            std::unique_lock<std::mutex> lock(event_mutex);
            if (event_cv.wait_for(lock, std::chrono::seconds(1), 
                [this] { return !event_queue.empty(); })) {
                auto event = event_queue.front();
                event_queue.pop();
                lock.unlock();

                // Access both timestamp and event details
                video_recorder.SaveVideo(Logger::GetCurrentTimestamp(), event.second, http_client);
            }
        }
    }).detach();
}

void EventMonitor::StopMonitoring() {
    is_monitoring = false;
    if (subscription) {
        EvtClose(subscription);
        subscription = NULL;
    }
}