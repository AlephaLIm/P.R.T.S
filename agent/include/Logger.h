#pragma once
#include <string>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <ctime>
#include <chrono>

class Logger {
public:
    static void Log(const std::wstring& message);
    static std::wstring GetCurrentTimestamp();

private:
    Logger() = default;
};