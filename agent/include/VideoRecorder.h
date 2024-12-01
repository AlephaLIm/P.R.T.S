#pragma once
#include "NetworkCommon.h"  // This must come first
#include <deque>
#include <mutex>
#include <filesystem>
#include <fstream>
#include <chrono>
#include <thread>
#include "Configuration.h"
#include "Logger.h"

class VideoRecorder {
public:
    VideoRecorder();
    void StartRecording();
    void StopRecording();
    void SaveVideo(const std::wstring& timestamp, const std::string& eventDetails, HttpClient &client);
    std::deque<std::wstring>& GetBufferFiles() { return buffer_files; }
    std::mutex& GetBufferMutex() { return buffer_mutex; }

private:
    std::deque<std::wstring> buffer_files;
    std::mutex buffer_mutex;
    FILE* ffmpeg_pipe;
    bool is_recording;
};