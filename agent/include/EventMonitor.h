#pragma once
#include "NetworkCommon.h"  // This must come first
#include <winevt.h>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <chrono>
#include "VideoRecorder.h"
#include "Logger.h"
#include "pugixml\pugixml.hpp"

class EventMonitor {
public:
    EventMonitor(VideoRecorder& recorder, HttpClient &client);
    void StartMonitoring();
    void StopMonitoring();
    static DWORD WINAPI SubscriptionCallback(EVT_SUBSCRIBE_NOTIFY_ACTION action, PVOID pContext, EVT_HANDLE hEvent);

private:
    VideoRecorder& video_recorder;
    HttpClient &http_client;
    EVT_HANDLE subscription;
    std::queue<std::pair<std::chrono::system_clock::time_point, std::string>> event_queue;
    std::mutex event_mutex;
    std::condition_variable event_cv;
    bool is_monitoring;
    std::string LogEventDetails(EVT_HANDLE hEvent);  // New method for detailed event logging
    json XMLNodeToJson(const pugi::xml_node& node);
};