#pragma once

#include <string>
#include <vector>

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

    bool login();
    void showMainMenu();
    void showHealth() const;
    void listCameras() const;
    void addCamera();
    void startRecording();
    void stopRecording();
    void showStorageVolumes() const;

    std::string serverUrl_;
    std::string accessToken_;
};

}  // namespace vms::client
