#include "Configuration.h"

// Function to get local hostname
std::string getHostname()
{
    char hostname[256];
    if (gethostname(hostname, sizeof(hostname)) != 0)
    {
        throw std::runtime_error("Failed to get hostname");
    }
    return std::string(hostname);
}

// Function to get local IP address
std::string getLocalIPAddress()
{
    // Initialize Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        throw std::runtime_error("WSAStartup failed");
    }

    // Get local hostname
    char hostname[256];
    if (gethostname(hostname, sizeof(hostname)) != 0)
    {
        WSACleanup();
        throw std::runtime_error("Failed to get hostname");
    }

    // Get local IP
    struct addrinfo hints, *res;
    ZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_INET; // IPv4
    hints.ai_socktype = SOCK_STREAM;

    if (getaddrinfo(hostname, NULL, &hints, &res) != 0)
    {
        WSACleanup();
        throw std::runtime_error("Failed to get address info");
    }

    char ipstr[INET_ADDRSTRLEN];
    struct sockaddr_in *addr = (struct sockaddr_in *)res->ai_addr;
    inet_ntop(AF_INET, &(addr->sin_addr), ipstr, INET_ADDRSTRLEN);

    freeaddrinfo(res);
    WSACleanup();

    return std::string(ipstr);
}

Configuration &Configuration::getInstance()
{
    static Configuration instance;
    return instance;
}

Configuration::Configuration() {}

Resolution Configuration::GetScreenResolution()
{
    Resolution res;
    res.width = GetSystemMetrics(SM_CXSCREEN);
    res.height = GetSystemMetrics(SM_CYSCREEN);
    return res;
}

std::wstring Configuration::ConvertToWString(const std::string &str)
{
    if (str.empty())
        return std::wstring();
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), NULL, 0);
    std::wstring wstrTo(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), &wstrTo[0], size_needed);
    return wstrTo;
}

bool Configuration::loadConfig(const std::wstring &configFile, HttpClient &client, std::wstring host, INTERNET_PORT port)
{
    std::cout << "Attempting to load config";
    try
    {
        std::ifstream f("config.json");
        if (!f.is_open())
        {
            std::cout << "Config file not found";
            if (registerWithServer(configFile, client, host, port))
            {
                return true;
            }
            else
            {
                return false;
            }
        }

        std::cout << "Config file found";
        json j;
        f >> j;

        std::cout << "Checking GUID";
        auto &identity = j["identity"];
        std::string temp_guid = identity["guid"];
        std::cout << "GUID is : " + temp_guid;
        json update_data = {
            {"guid", temp_guid},
            {"hostname", getHostname()},
            {"ip_addr", getLocalIPAddress()}};
        std::string update_request_body = update_data.dump();
        std::string post_response = client.Post(host, L"/update", update_request_body, L"application/json", port);
        std::cout << "\n\n\n\n POST RESPONSE \n\n\n\n" + post_response;
        json jpost = json::parse(post_response);
        auto &recording = jpost["recording"];
        config.pre_event_duration = recording["pre_event_duration"];
        config.post_event_duration = recording["post_event_duration"];
        config.duration_buffer = recording["duration_buffer"];
        config.fps = recording["fps"];
        config.resolution.width = recording["resolution"]["width"];
        config.resolution.height = recording["resolution"]["height"];
        config.segment_duration = jpost["buffer"]["segment_duration"];

        // Load event monitor configuration
        auto &event_monitor = jpost["event_monitor"];
        config.event_monitor.channel_path = ConvertToWString(event_monitor["channel_path"].get<std::string>());
        config.event_monitor.event_id = event_monitor["event_id"];

        
        config.guid = temp_guid;
        if (config.resolution.width == 0 || config.resolution.height == 0)
        {
            Resolution screenRes = GetScreenResolution();
            config.resolution = screenRes;
            Logger::Log(L"Using screen resolution: " +
                        std::to_wstring(screenRes.width) + L"x" +
                        std::to_wstring(screenRes.height));
        }

        config.total_duration = config.pre_event_duration + config.post_event_duration;

        return true;
    }
    catch (const std::exception &e)
    {
        // createDefaultConfig(configFile);

        return false;
    }
}

bool Configuration::registerWithServer(const std::wstring &configFile, HttpClient &client, std::wstring host, INTERNET_PORT port)
{
    try
    {
        std::cout << "\nmaking GET request to /register";
        std::string response = client.Get(host, L"/register", port);
        std::cout << "\nResponse: ";
        std::cout << response;
        // Parse the JSON response
        json j = json::parse(response);
        std::string temp_guid = j["guid"];
        std::cout << "\nGuid is: " + temp_guid;

        json registration_data = {
            {"guid", temp_guid},
            {"hostname", getHostname()},
            {"ip_addr", getLocalIPAddress()}};

        // Convert to string for sending
        std::string request_body = registration_data.dump();
        std::cout << "\n Making POST request to /register";
        std::string post_response = client.Post(host, L"/register", request_body, L"application/json", port);

        std::cout << "\nResponse is: " + post_response;
        json jpost = json::parse(post_response);

        // Write the JSON to config.json with proper formatting
        std::ofstream config_file("config.json");
        if (!config_file.is_open())
        {
            throw std::runtime_error("Failed to open config.json for writing");
        }
        config_file << std::setw(4) << jpost << std::endl;
        config_file.close();

        std::cout << "Configuration written to config.json\n";

        auto &recording = jpost["recording"];
        config.pre_event_duration = recording["pre_event_duration"];
        config.post_event_duration = recording["post_event_duration"];
        config.duration_buffer = recording["duration_buffer"];
        config.fps = recording["fps"];
        config.resolution.width = recording["resolution"]["width"];
        config.resolution.height = recording["resolution"]["height"];
        config.segment_duration = jpost["buffer"]["segment_duration"];

        // Load event monitor configuration
        auto &event_monitor = jpost["event_monitor"];
        config.event_monitor.channel_path = ConvertToWString(event_monitor["channel_path"].get<std::string>());
        config.event_monitor.event_id = event_monitor["event_id"];

        auto &identity = jpost["identity"];
        config.guid = identity["guid"];

        if (config.resolution.width == 0 || config.resolution.height == 0)
        {
            Resolution screenRes = GetScreenResolution();
            config.resolution = screenRes;
            Logger::Log(L"Using screen resolution: " +
                        std::to_wstring(screenRes.width) + L"x" +
                        std::to_wstring(screenRes.height));
        }

        config.total_duration = config.pre_event_duration + config.post_event_duration;

        return true;
    }
    catch (const std::exception &e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
        return false;
    }
}

const RecordingConfig &Configuration::getConfig() const
{
    return config;
}