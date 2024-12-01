#include "VideoRecorder.h"

VideoRecorder::VideoRecorder() : ffmpeg_pipe(nullptr), is_recording(false)
{
    std::filesystem::create_directory("buffers");
}

void VideoRecorder::StartRecording()
{
    const auto &config = Configuration::getInstance().getConfig();

    std::wstring ffmpeg_command = L"ffmpeg -f gdigrab -framerate " +
                                  std::to_wstring(config.fps) +
                                  L" -video_size " +
                                  std::to_wstring(config.resolution.width) + L"x" +
                                  std::to_wstring(config.resolution.height) +
                                  L" -i desktop " +
                                  L"-c:v libx264 -preset ultrafast -crf 23 "
                                  L"-force_key_frames expr:gte(t,0) "
                                  L"-x264opts keyint=60:min-keyint=60 "
                                  L"-f segment -segment_time " +
                                  std::to_wstring(config.segment_duration) + L" "
                                                                             L"-segment_format mpegts "
                                                                             L"-reset_timestamps 1 "
                                                                             L"buffers\\segment%03d.ts";

    Logger::Log(L"Starting FFmpeg with command: " + ffmpeg_command);

    ffmpeg_pipe = _wpopen(ffmpeg_command.c_str(), L"w");
    if (!ffmpeg_pipe)
    {
        Logger::Log(L"Error starting FFmpeg process");
        return;
    }

    is_recording = true;
    Logger::Log(L"FFmpeg process started successfully");
}

void VideoRecorder::StopRecording()
{
    if (ffmpeg_pipe)
    {
        Logger::Log(L"Stopping FFmpeg process");
        fputc('q', ffmpeg_pipe);
        fflush(ffmpeg_pipe);
        _pclose(ffmpeg_pipe);
        ffmpeg_pipe = nullptr;
    }
    is_recording = false;
}

void VideoRecorder::SaveVideo(const std::wstring &timestamp, const std::string &eventDetails, HttpClient &client)
{
    
    std::cout << "\n\n\n\n\n JSON:" + eventDetails + "\n\n\n\n";
    Logger::Log(L"Starting video save process for event detected at: " + timestamp);
    const auto &config = Configuration::getInstance().getConfig();

    int adjusted_post_duration = config.post_event_duration + config.duration_buffer;

    // Wait for post-event duration to complete first
    Logger::Log(L"Waiting for post-event duration: " + std::to_wstring(config.post_event_duration) + L" seconds");
    std::this_thread::sleep_for(std::chrono::seconds(adjusted_post_duration));

    // Get current buffer files
    std::unique_lock<std::mutex> lock(buffer_mutex);
    auto buffer_files_copy = buffer_files;
    lock.unlock();

    if (buffer_files_copy.empty())
    {
        Logger::Log(L"No buffer files available. Cannot save video.");
        return;
    }

    // Create output filename
    std::wstring output_filename = L"event_" + timestamp + L".mp4";
    std::wstring temp_combined = L"temp_combined.ts";

    // First, concatenate all buffer files
    std::wstring concat_list = L"concat_list.txt";
    {
        std::wofstream list_file(concat_list);
        for (const auto &file : buffer_files_copy)
        {
            list_file << "file '" << file << "'\n";
        }
        list_file.close();
    }

    // Create temporary combined file
    std::wstring concat_command = L"ffmpeg -f concat -safe 0 -i " + concat_list +
                                  L" -c copy -y " + temp_combined;

    Logger::Log(L"Creating temporary combined file...");
    int result = _wsystem(concat_command.c_str());
    if (result != 0)
    {
        Logger::Log(L"Error creating temporary combined file.");
        std::filesystem::remove(concat_list);
        return;
    }

    // Extract the required duration from the combined file with improved encoding settings
    int total_duration = config.pre_event_duration + adjusted_post_duration;
    std::wstring extract_command = L"ffmpeg -sseof -" + std::to_wstring(total_duration) +
                                   L" -i " + temp_combined +
                                   L" -t " + std::to_wstring(config.pre_event_duration + config.post_event_duration) +
                                   L" -c:v libx264 -preset fast -crf 23 "
                                   L"-force_key_frames expr:gte(t,0) "   // Force keyframe at start
                                   L"-x264opts keyint=60:min-keyint=60 " // Regular keyframes every 2 seconds
                                   L"-movflags +faststart "              // Enable fast start for better playback
                                   L"-video_track_timescale 30000 "      // Improve timestamp precision
                                   L"-y " +
                                   output_filename;

    Logger::Log(L"Creating final video...");
    Logger::Log(L"Executing command: " + extract_command);
    result = _wsystem(extract_command.c_str());
    if (result != 0)
    {
        Logger::Log(L"Error creating final video");
    }
    else
    {
        Logger::Log(L"Video successfully saved as: " + output_filename);
    }

    // Cleanup temporary files
    std::filesystem::remove(concat_list);
    std::filesystem::remove(temp_combined);

    Logger::Log(L"Video save process completed");

    // upload video here
    std::wstring wstring_guid(config.guid.begin(), config.guid.end());
    std::wstring api_path = L"/agent_trigger?guid=" + wstring_guid;
    HttpResponse response = client.UploadFileWithJson(
        client.host,
        api_path,
        output_filename,
        eventDetails, // Your JSON string
        client.port);
    
    std::cout << "\n\n\nStatus code: " << response.statusCode << std::endl;
    std::cout << "\n\n\nResponse: " << response.content << std::endl;
}