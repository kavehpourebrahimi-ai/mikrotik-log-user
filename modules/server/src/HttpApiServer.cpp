#include "vms/server/HttpApiServer.hpp"

#include "vms/common/Uuid.hpp"
#include "vms/common/Logging.hpp"
#include "vms/core/Types.hpp"

#include <httplib.h>
#include <nlohmann/json.hpp>

#include <chrono>
#include <filesystem>
#include <fstream>

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
    std::shared_ptr<IOnvifDiscovery> onvifDiscovery,
    std::filesystem::path auditLogPath,
    int port)
    : cameraRepository_(std::move(cameraRepository)),
      recordingEngine_(std::move(recordingEngine)),
      storageManager_(std::move(storageManager)),
      authenticationService_(std::move(authenticationService)),
      onvifDiscovery_(std::move(onvifDiscovery)),
      auditLogPath_(std::move(auditLogPath)),
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

    server_->Get("/", [](const httplib::Request&, httplib::Response& res) {
        constexpr auto kHtml = R"HTML(
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Enterprise VMS Dashboard</title>
  <style>
    body{font-family:Arial,sans-serif;max-width:960px;margin:24px auto;padding:0 12px;background:#f6f8fb}
    .card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:16px;margin-bottom:12px}
    h1{color:#0b3b82}.row{display:flex;gap:8px;flex-wrap:wrap}
    input,button{padding:8px;border-radius:6px;border:1px solid #bbb}
    button{background:#0b3b82;color:#fff;border:none;cursor:pointer}
    pre{background:#111;color:#7cff7c;padding:12px;border-radius:8px;overflow:auto}
  </style>
</head>
<body>
  <h1>Enterprise VMS Web UI</h1>
  <div class="card">
    <h3>Login</h3>
    <div class="row">
      <input id="u" placeholder="username" value="admin" />
      <input id="p" placeholder="password" value="admin" type="password" />
      <button onclick="login()">Login</button>
    </div>
  </div>
  <div class="card">
    <h3>Health & Cameras</h3>
    <button onclick="health()">Health</button>
    <button onclick="listCams()">List Cameras</button>
  </div>
  <div class="card">
    <h3>Add Camera</h3>
    <div class="row">
      <input id="name" placeholder="Camera name" value="Lobby" />
      <input id="host" placeholder="Host/IP" value="192.168.1.10" />
      <input id="uri" placeholder="Main RTSP URI" value="rtsp://192.168.1.10/main" style="min-width:300px" />
      <button onclick="addCam()">Add</button>
    </div>
  </div>
  <div class="card">
    <h3>Recording Controls</h3>
    <div class="row">
      <input id="cid" placeholder="Camera ID" />
      <button onclick="recStart()">Start</button>
      <button onclick="recStop()">Stop</button>
      <button onclick="recFiles()">Files</button>
      <button onclick="discover()">ONVIF Discover</button>
    </div>
  </div>
  <div class="card"><pre id="out">Ready.</pre></div>
<script>
let token = "";
const out = document.getElementById("out");
const j = (obj)=>JSON.stringify(obj,null,2);
async function req(method,path,body){
  const headers={"Content-Type":"application/json"};
  if(token) headers["Authorization"]="Bearer "+token;
  const r=await fetch(path,{method,headers,body:body?JSON.stringify(body):undefined});
  const t=await r.text();
  try{return {status:r.status,data:JSON.parse(t)}}catch{return {status:r.status,data:t}}
}
async function login(){
  const r=await req("POST","/api/v1/auth/login",{username:u.value,password:p.value});
  if(r.data.access_token) token=r.data.access_token;
  out.textContent=j(r);
}
async function health(){ out.textContent=j(await req("GET","/api/v1/health")); }
async function listCams(){ out.textContent=j(await req("GET","/api/v1/cameras")); }
async function addCam(){ out.textContent=j(await req("POST","/api/v1/cameras",{name:name.value,host:host.value,mainStreamUri:uri.value})); }
async function recStart(){ out.textContent=j(await req("POST","/api/v1/cameras/"+cid.value+"/record/start",{})); }
async function recStop(){ out.textContent=j(await req("POST","/api/v1/cameras/"+cid.value+"/record/stop",{})); }
async function recFiles(){ out.textContent=j(await req("GET","/api/v1/cameras/"+cid.value+"/record/files")); }
async function discover(){ out.textContent=j(await req("POST","/api/v1/onvif/discover",{timeoutMs:1500})); }
</script>
</body>
</html>
)HTML";
        res.set_content(kHtml, "text/html; charset=utf-8");
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
        writeAuditEntry("login", username, "success");

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
        writeAuditEntry("camera_upsert", "api", camera.id.value);

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
            writeAuditEntry("camera_remove", "api", cameraId.value);

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
            writeAuditEntry("record_start", "api", cameraId.value);

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
            writeAuditEntry("record_stop", "api", cameraId.value);

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

    server_->Get(
        R"(/api/v1/cameras/([^/]+)/record/files)",
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

            json files = json::array();
            for (const auto& volume : storageManager_->listVolumes()) {
                const auto cameraDir = std::filesystem::path(volume.mountPath) / cameraId.value;
                if (!std::filesystem::exists(cameraDir)) {
                    continue;
                }
                for (const auto& entry : std::filesystem::directory_iterator(cameraDir)) {
                    if (!entry.is_regular_file()) {
                        continue;
                    }
                    files.push_back({
                        {"path", entry.path().string()},
                        {"size_bytes", entry.file_size()},
                        {"name", entry.path().filename().string()},
                    });
                }
            }

            respondJson(res, 200, json{{"cameraId", cameraId.value}, {"items", files}});
        });

    server_->Post("/api/v1/onvif/discover", [this](const httplib::Request& req, httplib::Response& res) {
        const auto token = extractBearerToken(req);
        if (token.empty() || !authenticationService_->validateToken(token).ok()) {
            respondJson(res, 401, json{{"error", "Unauthorized"}});
            return;
        }

        if (!onvifDiscovery_) {
            respondJson(res, 500, json{{"error", "ONVIF discovery service unavailable"}});
            return;
        }

        json payload = json::object();
        if (!req.body.empty()) {
            try {
                payload = json::parse(req.body);
            } catch (...) {
                respondJson(res, 400, json{{"error", "Invalid JSON payload"}});
                return;
            }
        }
        const auto timeoutMs = payload.value("timeoutMs", 1500);
        const auto result = onvifDiscovery_->discover(Duration{timeoutMs});
        if (!result.ok()) {
            respondJson(res, 400, json{{"error", result.error}});
            return;
        }

        json items = json::array();
        for (const auto& cam : *result.value) {
            items.push_back({
                {"id", cam.id.value},
                {"name", cam.name},
                {"host", cam.host},
                {"mainStreamUri", cam.mainStreamUri},
                {"subStreamUri", cam.subStreamUri},
            });
        }
        writeAuditEntry("onvif_discover", "api", "count=" + std::to_string(items.size()));
        respondJson(res, 200, json{{"items", items}});
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

void HttpApiServer::writeAuditEntry(
    std::string_view action,
    std::string_view principal,
    std::string_view details) const {
    std::lock_guard lock(auditMutex_);
    std::filesystem::create_directories(auditLogPath_.parent_path());
    std::ofstream out(auditLogPath_, std::ios::app);
    if (!out.is_open()) {
        return;
    }
    const auto nowMs = std::chrono::duration_cast<std::chrono::milliseconds>(
                           std::chrono::system_clock::now().time_since_epoch())
                           .count();
    out << nowMs << "," << action << "," << principal << "," << details << "\n";
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
