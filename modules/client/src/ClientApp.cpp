#include "vms/client/ClientApp.hpp"

#include "vms/common/Logging.hpp"

#include <httplib.h>
#include <nlohmann/json.hpp>

#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>

namespace vms::client {
namespace {
using json = nlohmann::json;

std::optional<httplib::Result> sendJsonRequest(
    httplib::Client& client,
    const std::string& method,
    const std::string& path,
    const std::string& token,
    const json& payload = {}) {
    httplib::Headers headers;
    headers.emplace("Content-Type", "application/json");
    if (!token.empty()) {
        headers.emplace("Authorization", "Bearer " + token);
    }

    if (method == "GET") {
        return client.Get(path.c_str(), headers);
    }
    if (method == "POST") {
        return client.Post(path.c_str(), headers, payload.dump(), "application/json");
    }
    return std::nullopt;
}

void printTitle(const std::string& title) {
    std::cout << "\n===========================================\n";
    std::cout << title << '\n';
    std::cout << "===========================================\n";
}
}  // namespace

int ClientApp::run(int argc, char** argv) {
    const auto serverUrl = parseServerUrl(argc, argv);
    if (serverUrl.empty()) {
        printUsage();
        return 1;
    }
    serverUrl_ = serverUrl;

    printBanner();
    vms::logger().log(vms::LogLevel::Info, "vms_client", "Target server: " + serverUrl_);

    if (!login()) {
        std::cerr << "Login failed.\n";
        return 1;
    }

    showMainMenu();

    return 0;
}

void ClientApp::printBanner() {
    std::cout << "Enterprise VMS Windows Client (Phase 1 bootstrap)\n";
    std::cout << "--------------------------------------------------\n";
}

void ClientApp::printUsage() {
    std::cout << "Usage: vms_client --server <url>\n";
    std::cout << "Example: vms_client --server http://127.0.0.1:8080\n";
}

std::string ClientApp::prompt(const std::string& label) {
    std::cout << label;
    std::string value;
    std::getline(std::cin, value);
    return value;
}

bool ClientApp::login() {
    printTitle("VMS Login");
    const auto username = prompt("Username (default admin): ");
    const auto password = prompt("Password (default admin): ");

    httplib::Client client(serverUrl_);
    client.set_connection_timeout(5);
    client.set_read_timeout(10);

    json body{
        {"username", username.empty() ? "admin" : username},
        {"password", password.empty() ? "admin" : password},
    };

    auto response = sendJsonRequest(client, "POST", "/api/v1/auth/login", {}, body);
    if (!response || !*response || (*response)->status != 200) {
        std::cerr << "Authentication request failed.\n";
        return false;
    }

    json parsed;
    try {
        parsed = json::parse((*response)->body);
    } catch (...) {
        std::cerr << "Invalid login response from server.\n";
        return false;
    }

    if (!parsed.contains("access_token")) {
        std::cerr << "No access token in login response.\n";
        return false;
    }
    accessToken_ = parsed["access_token"].get<std::string>();
    return true;
}

void ClientApp::showMainMenu() {
    while (true) {
        printTitle("Enterprise VMS Client Menu");
        std::cout << "1) Server health\n";
        std::cout << "2) List cameras\n";
        std::cout << "3) Add camera\n";
        std::cout << "4) Start recording\n";
        std::cout << "5) Stop recording\n";
        std::cout << "6) Storage volumes\n";
        std::cout << "0) Exit\n";

        const auto choice = prompt("Select: ");
        if (choice == "1") {
            showHealth();
        } else if (choice == "2") {
            listCameras();
        } else if (choice == "3") {
            addCamera();
        } else if (choice == "4") {
            startRecording();
        } else if (choice == "5") {
            stopRecording();
        } else if (choice == "6") {
            showStorageVolumes();
        } else if (choice == "0") {
            return;
        } else {
            std::cout << "Invalid option.\n";
        }
    }
}

void ClientApp::showHealth() const {
    httplib::Client client(serverUrl_);
    client.set_connection_timeout(5);
    client.set_read_timeout(10);
    const auto response = client.Get("/api/v1/health");

    if (!response || response->status != 200) {
        std::cout << "Failed to fetch health.\n";
        return;
    }

    std::cout << response->body << '\n';
}

void ClientApp::listCameras() const {
    httplib::Client client(serverUrl_);
    client.set_connection_timeout(5);
    client.set_read_timeout(10);

    auto response = sendJsonRequest(client, "GET", "/api/v1/cameras", accessToken_);
    if (!response || !*response || (*response)->status != 200) {
        std::cout << "Failed to list cameras.\n";
        return;
    }

    json parsed;
    try {
        parsed = json::parse((*response)->body);
    } catch (...) {
        std::cout << "Invalid response.\n";
        return;
    }

    if (!parsed.contains("items") || !parsed["items"].is_array()) {
        std::cout << "No cameras.\n";
        return;
    }

    std::cout << "\nCameras:\n";
    for (const auto& cam : parsed["items"]) {
        std::cout << " - [" << cam.value("id", "") << "] "
                  << cam.value("name", "Unnamed")
                  << " host=" << cam.value("host", "")
                  << " enabled=" << (cam.value("enabled", true) ? "yes" : "no")
                  << '\n';
    }
}

void ClientApp::addCamera() {
    const auto name = prompt("Camera name: ");
    const auto host = prompt("Camera host/ip: ");
    const auto mainUri = prompt("Main RTSP URI: ");
    const auto subUri = prompt("Sub RTSP URI (optional): ");
    const auto user = prompt("Camera username (optional): ");
    const auto pass = prompt("Camera password (optional): ");

    if (host.empty() || mainUri.empty()) {
        std::cout << "host and main URI are required.\n";
        return;
    }

    json payload{
        {"name", name.empty() ? "Camera" : name},
        {"host", host},
        {"mainStreamUri", mainUri},
        {"subStreamUri", subUri},
        {"username", user},
        {"password", pass},
    };

    httplib::Client client(serverUrl_);
    auto response = sendJsonRequest(client, "POST", "/api/v1/cameras", accessToken_, payload);
    if (!response || !*response) {
        std::cout << "Request failed.\n";
        return;
    }
    std::cout << (*response)->body << '\n';
}

void ClientApp::startRecording() {
    const auto cameraId = prompt("Camera ID: ");
    if (cameraId.empty()) {
        std::cout << "Camera ID required.\n";
        return;
    }

    httplib::Client client(serverUrl_);
    auto response = sendJsonRequest(
        client,
        "POST",
        "/api/v1/cameras/" + cameraId + "/record/start",
        accessToken_,
        json::object());
    if (!response || !*response) {
        std::cout << "Request failed.\n";
        return;
    }
    std::cout << (*response)->body << '\n';
}

void ClientApp::stopRecording() {
    const auto cameraId = prompt("Camera ID: ");
    if (cameraId.empty()) {
        std::cout << "Camera ID required.\n";
        return;
    }

    httplib::Client client(serverUrl_);
    auto response = sendJsonRequest(
        client,
        "POST",
        "/api/v1/cameras/" + cameraId + "/record/stop",
        accessToken_,
        json::object());
    if (!response || !*response) {
        std::cout << "Request failed.\n";
        return;
    }
    std::cout << (*response)->body << '\n';
}

void ClientApp::showStorageVolumes() const {
    httplib::Client client(serverUrl_);
    auto response = sendJsonRequest(client, "GET", "/api/v1/storage/volumes", accessToken_);
    if (!response || !*response) {
        std::cout << "Request failed.\n";
        return;
    }
    std::cout << (*response)->body << '\n';
}

std::string ClientApp::parseServerUrl(int argc, char** argv) {
    for (int i = 1; i + 1 < argc; ++i) {
        if (std::string(argv[i]) == "--server") {
            return argv[i + 1];
        }
    }
    return {};
}

}  // namespace vms::client
