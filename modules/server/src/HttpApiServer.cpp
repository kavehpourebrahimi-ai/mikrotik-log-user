#include "vms/server/HttpApiServer.hpp"

#include "vms/common/Uuid.hpp"
#include "vms/common/Logging.hpp"
#include "vms/core/Types.hpp"

#include <httplib.h>
#include <nlohmann/json.hpp>

#include <chrono>

namespace vms {
namespace {

using json = nlohmann::json;

std::string extractBearerToken(const httplib::Request& request) {
    const auto authHeader = request.get_header_value("Authorization");
    constexpr std::string_view prefix = "Bearer ";
    if (authHeader.rfind(prefix, 0) == 0) {
        return authHeader.substr(prefix.size());
    }
    return {};
}

void respondJson(httplib::Response& response, int status, const json& payload) {
    response.status = status;
    response.set_content(payload.dump(), "application/json");
}

std::string getStringOrDefault(
    const json& payload,
    const char* key,
    const std::string& fallback = {}) {
    if (!payload.contains(key) || payload[key].is_null()) {
        return fallback;
    }
    return payload[key].get<std::string>();
}

}  // namespace

HttpApiServer::HttpApiServer(
    std::shared_ptr<ICameraRepository> cameraRepository,
    std::shared_ptr<IRecordingEngine> recordingEngine,
    std::shared_ptr<IStorageManager> storageManager,
    std::shared_ptr<IAuthenticationService> authenticationService,
    int port)
    : cameraRepository_(std::move(cameraRepository)),
      recordingEngine_(std::move(recordingEngine)),
      storageManager_(std::move(storageManager)),
      authenticationService_(std::move(authenticationService)),
      port_(port),
      server_(std::make_unique<httplib::Server>()) {}

HttpApiServer::~HttpApiServer() {
    stop();
}

Result<void> HttpApiServer::start() {
    if (running_.exchange(true)) {
        return Result<void>::success();
    }

    const auto startedAt = std::chrono::system_clock::now();

    server_->Get("/api/v1/health", [startedAt, this](const httplib::Request&, httplib::Response& res) {
        const auto uptime = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now() - startedAt);
        const auto cameras = cameraRepository_->list();

        respondJson(
            res,
            200,
            json{
                {"status", "ok"},
                {"service", "enterprise-vms-server"},
                {"uptime_seconds", uptime.count()},
                {"camera_count", cameras.size()},
                {"recording_engine", "ready"},
                {"api_version", "v1"}});
    });

    server_->Post("/api/v1/auth/login", [this](const httplib::Request& req, httplib::Response& res) {
        json payload;
        try {
            payload = json::parse(req.body);
        } catch (...) {
            respondJson(res, 400, json{{"error", "Invalid JSON payload"}});
            return;
        }

        const auto username = getStringOrDefault(payload, "username");
        const auto password = getStringOrDefault(payload, "password");
        if (username.empty() || password.empty()) {
            respondJson(res, 400, json{{"error", "username and password are required"}});
            return;
        }

        const auto tokenResult = authenticationService_->authenticate(username, password);
        if (!tokenResult.ok()) {
            respondJson(res, 401, json{{"error", tokenResult.error}});
            return;
        }

        respondJson(
            res,
            200,
            json{{"access_token", *tokenResult.value}, {"token_type", "Bearer"}});
    });

    server_->Get("/api/v1/cameras", [this](const httplib::Request& req, httplib::Response& res) {
        const auto token = extractBearerToken(req);
        if (token.empty() || !authenticationService_->validateToken(token).ok()) {
            respondJson(res, 401, json{{"error", "Unauthorized"}});
            return;
        }

        json cameras = json::array();
        for (const auto& camera : cameraRepository_->list()) {
            cameras.push_back(
                {
                    {"id", camera.id.value},
                    {"name", camera.name},
                    {"host", camera.host},
                    {"port", camera.port},
                    {"mainStreamUri", camera.mainStreamUri},
                    {"subStreamUri", camera.subStreamUri},
                    {"enabled", camera.enabled},
                });
        }
        respondJson(res, 200, json{{"items", cameras}});
    });

    server_->Post("/api/v1/cameras", [this](const httplib::Request& req, httplib::Response& res) {
        const auto token = extractBearerToken(req);
        if (token.empty() || !authenticationService_->validateToken(token).ok()) {
            respondJson(res, 401, json{{"error", "Unauthorized"}});
            return;
        }

        json payload;
        try {
            payload = json::parse(req.body);
        } catch (...) {
            respondJson(res, 400, json{{"error", "Invalid JSON payload"}});
            return;
        }

        CameraDescriptor camera;
        camera.id = CameraId{getStringOrDefault(payload, "id", "")};
        if (camera.id.value.empty()) {
            camera.id = CameraId{generateUuid()};
        }
        camera.name = getStringOrDefault(payload, "name", "Unnamed Camera");
        camera.host = getStringOrDefault(payload, "host");
        camera.port = payload.value("port", static_cast<std::uint16_t>(554));
        camera.mainStreamUri = getStringOrDefault(payload, "mainStreamUri");
        camera.subStreamUri = getStringOrDefault(payload, "subStreamUri");
        camera.username = getStringOrDefault(payload, "username");
        camera.password = getStringOrDefault(payload, "password");
        camera.enabled = payload.value("enabled", true);
        camera.status = camera.enabled ? CameraStatus::Online : CameraStatus::Disabled;

        if (camera.host.empty() || camera.mainStreamUri.empty()) {
            respondJson(res, 400, json{{"error", "host and mainStreamUri are required"}});
            return;
        }

        const auto upsertResult = cameraRepository_->upsert(camera);
        if (!upsertResult.ok()) {
            respondJson(res, 400, json{{"error", upsertResult.error}});
            return;
        }

        respondJson(res, 201, json{{"id", camera.id.value}, {"status", "created"}});
    });

    server_->Delete(
        R"(/api/v1/cameras/([^/]+))",
        [this](const httplib::Request& req, httplib::Response& res) {
            const auto token = extractBearerToken(req);
            if (token.empty() || !authenticationService_->validateToken(token).ok()) {
                respondJson(res, 401, json{{"error", "Unauthorized"}});
                return;
            }

            const CameraId cameraId{req.matches[1]};
            const auto removeResult = cameraRepository_->remove(cameraId);
            if (!removeResult.ok()) {
                respondJson(res, 404, json{{"error", removeResult.error}});
                return;
            }

            respondJson(res, 200, json{{"cameraId", cameraId.value}, {"status", "deleted"}});
        });

    server_->Post(
        R"(/api/v1/cameras/([^/]+)/record/start)",
        [this](const httplib::Request& req, httplib::Response& res) {
            const auto token = extractBearerToken(req);
            if (token.empty() || !authenticationService_->validateToken(token).ok()) {
                respondJson(res, 401, json{{"error", "Unauthorized"}});
                return;
            }

            const CameraId cameraId{req.matches[1]};
            const auto result = recordingEngine_->startRecording(cameraId, RecordingMode::Continuous);
            if (!result.ok()) {
                respondJson(res, 400, json{{"error", result.error}});
                return;
            }

            respondJson(res, 200, json{{"cameraId", cameraId.value}, {"recording", true}});
        });

    server_->Post(
        R"(/api/v1/cameras/([^/]+)/record/stop)",
        [this](const httplib::Request& req, httplib::Response& res) {
            const auto token = extractBearerToken(req);
            if (token.empty() || !authenticationService_->validateToken(token).ok()) {
                respondJson(res, 401, json{{"error", "Unauthorized"}});
                return;
            }

            const CameraId cameraId{req.matches[1]};
            const auto result = recordingEngine_->stopRecording(cameraId);
            if (!result.ok()) {
                respondJson(res, 400, json{{"error", result.error}});
                return;
            }

            respondJson(res, 200, json{{"cameraId", cameraId.value}, {"recording", false}});
        });

    server_->Get("/api/v1/storage/volumes", [this](const httplib::Request& req, httplib::Response& res) {
        const auto token = extractBearerToken(req);
        if (token.empty() || !authenticationService_->validateToken(token).ok()) {
            respondJson(res, 401, json{{"error", "Unauthorized"}});
            return;
        }

        json volumes = json::array();
        for (const auto& volume : storageManager_->listVolumes()) {
            volumes.push_back(
                {
                    {"id", volume.volumeId},
                    {"mountPath", volume.mountPath},
                    {"totalBytes", volume.totalBytes},
                    {"freeBytes", volume.freeBytes},
                    {"writable", volume.writable},
                });
        }
        respondJson(res, 200, json{{"items", volumes}});
    });

    server_->Get(
        R"(/api/v1/cameras/([^/]+)/record/status)",
        [this](const httplib::Request& req, httplib::Response& res) {
            const auto token = extractBearerToken(req);
            if (token.empty() || !authenticationService_->validateToken(token).ok()) {
                respondJson(res, 401, json{{"error", "Unauthorized"}});
                return;
            }

            const CameraId cameraId{req.matches[1]};
            const auto cameraLookup = cameraRepository_->get(cameraId);
            if (!cameraLookup.ok()) {
                respondJson(res, 404, json{{"error", cameraLookup.error}});
                return;
            }

            respondJson(
                res,
                200,
                json{
                    {"cameraId", cameraId.value},
                    {"recording", recordingEngine_->isRecording(cameraId)},
                });
        });

    serverThread_ = std::thread([this]() {
        logger().log(
            LogLevel::Info,
            "HttpApiServer",
            "REST API listening on http://0.0.0.0:" + std::to_string(port_));
        if (!server_->listen("0.0.0.0", port_)) {
            logger().log(LogLevel::Error, "HttpApiServer", "Failed to bind HTTP server");
        }
        running_.store(false);
    });

    return Result<void>::success();
}

void HttpApiServer::stop() {
    if (!running_.exchange(false)) {
        return;
    }

    if (server_) {
        server_->stop();
    }
    if (serverThread_.joinable()) {
        serverThread_.join();
    }
}

}  // namespace vms
