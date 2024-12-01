#include "Configuration.h"
#include "Logger.h"
#include "VideoRecorder.h"
#include "EventMonitor.h"
#include "HttpClient.h"

std::atomic<bool> keep_running(true);

BOOL WINAPI ConsoleHandler(DWORD ctrlType)
{
    if (ctrlType == CTRL_C_EVENT)
    {
        Logger::Log(L"Ctrl+C received. Stopping...");
        keep_running.store(false);
        return TRUE;
    }
    return FALSE;
}

void ManageBufferFiles(VideoRecorder &recorder)
{
    const int BUFFER_COUNT = 3;

    while (keep_running.load())
    {
        std::this_thread::sleep_for(std::chrono::seconds(1));

        std::unique_lock<std::mutex> lock(recorder.GetBufferMutex());
        for (const auto &entry : std::filesystem::directory_iterator("buffers"))
        {
            if (entry.path().extension() == L".ts" &&
                std::find(recorder.GetBufferFiles().begin(),
                          recorder.GetBufferFiles().end(),
                          entry.path().wstring()) == recorder.GetBufferFiles().end())
            {
                recorder.GetBufferFiles().push_back(entry.path().wstring());
            }
        }

        while (recorder.GetBufferFiles().size() > BUFFER_COUNT)
        {
            std::filesystem::remove(recorder.GetBufferFiles().front());
            recorder.GetBufferFiles().pop_front();
        }
        lock.unlock();
    }
}

int main(int argc, char *argv[])
{

    if (argc != 3)
    {
        std::cerr << "Usage: " << argv[0] << " <host> <port>\n";
        std::cerr << "Example: " << argv[0] << " localhost 8000\n";
        return 1;
    }
    
    std::string host_str = argv[1];
    std::wstring host(host_str.begin(), host_str.end());

    // Convert port from string to integer
    INTERNET_PORT port = static_cast<INTERNET_PORT>(std::stoi(argv[2]));

    HttpClient client;
    client.host = host;
    client.port = port;


    // Load configuration
    if (!Configuration::getInstance().loadConfig(L"config.json", client, host, port))
    {
        Logger::Log(L"Error loading configuration. Exiting...");
        return 1;
    }
   
    Logger::Log(L"Starting Symantec Event Monitor with Screen Recording...");
    // Clean up buffers directory
    try
    {
        if (std::filesystem::exists("buffers"))
        {
            for (const auto &entry : std::filesystem::directory_iterator("buffers"))
            {
                std::filesystem::remove_all(entry.path());
            }
        }
        Logger::Log(L"Buffers folder cleared successfully.");
    }
    catch (const std::filesystem::filesystem_error &e)
    {
        Logger::Log(L"Error clearing buffers folder: " +
                    std::wstring(e.what(), e.what() + strlen(e.what())));
    }

    // Set up Ctrl+C handler
    SetConsoleCtrlHandler(ConsoleHandler, TRUE);

    // Initialize and start components
    VideoRecorder recorder;
    EventMonitor monitor(recorder, client);

    recorder.StartRecording();
    monitor.StartMonitoring();

    // Start buffer management thread
    std::thread buffer_thread(ManageBufferFiles, std::ref(recorder));

    Logger::Log(L"Press Ctrl+C to exit.");

    // Main loop
    while (keep_running.load())
    {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    // Cleanup
    monitor.StopMonitoring();
    recorder.StopRecording();
    buffer_thread.join();

    Logger::Log(L"Program terminated.");
    return 0;
}