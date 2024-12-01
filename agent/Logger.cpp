#include "Logger.h"

void Logger::Log(const std::wstring& message) {
    std::wcout << L"[" << GetCurrentTimestamp() << L"] " << message << std::endl;
}

std::wstring Logger::GetCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto in_time_t = std::chrono::system_clock::to_time_t(now);
    struct tm timeinfo;
    localtime_s(&timeinfo, &in_time_t);
    std::wostringstream woss;
    woss << std::setfill(L'0')
         << std::setw(4) << (timeinfo.tm_year + 1900)
         << std::setw(2) << (timeinfo.tm_mon + 1)
         << std::setw(2) << timeinfo.tm_mday
         << L"_"
         << std::setw(2) << timeinfo.tm_hour
         << std::setw(2) << timeinfo.tm_min
         << std::setw(2) << timeinfo.tm_sec;
    return woss.str();
}