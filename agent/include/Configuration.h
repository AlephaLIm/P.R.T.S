#pragma once
#include "NetworkCommon.h"  // This must come first
#include <nlohmann/json.hpp>
#include "Logger.h"
#include "HttpClient.h"

using json = nlohmann::json;

struct Resolution {
    int width;
    int height;
};

struct EventMonitorConfig {
    std::wstring channel_path;
    int event_id;
};

struct RecordingConfig {
    int pre_event_duration;
    int post_event_duration;
    int duration_buffer;
    int fps;
    Resolution resolution;
    int segment_duration;
    int total_duration;  // Calculated field
    EventMonitorConfig event_monitor;
    std::string guid;
};

class Configuration {
public:
    static Configuration& getInstance();
    bool loadConfig(const std::wstring& configFile, HttpClient &client, std::wstring host, INTERNET_PORT port);
    const RecordingConfig& getConfig() const;

private:
    Configuration();
    bool registerWithServer(const std::wstring& configFile, HttpClient &client, std::wstring host, INTERNET_PORT port);
    Resolution GetScreenResolution();
    std::wstring ConvertToWString(const std::string& str);
    RecordingConfig config;
};