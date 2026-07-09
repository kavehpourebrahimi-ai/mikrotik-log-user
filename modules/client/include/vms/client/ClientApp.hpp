#pragma once

#include <string>
#include <vector>

namespace httplib {
class Client;
class Result;
}

namespace vms::client {

/// @brief Interactive VMS client shell with operational menu.
class ClientApp {
public:
    int run(int argc, char** argv);

private:
    static void printBanner();
    static void printUsage();
    static std::string parseServerUrl(int argc, char** argv);
    static std::string prompt(const std::string& label);
    bool ensureAuthenticated();
    bool handleUnauthorizedAndRetry() const;

    bool login();
    void showMainMenu();
    void showHealth() const;
    void listCameras() const;
    void addCamera();
    void removeCamera();
    void startRecording();
    void stopRecording();
    void showRecordingStatus() const;
    void showStorageVolumes() const;

    std::string serverUrl_;
    std::string accessToken_;
};

}  // namespace vms::client
