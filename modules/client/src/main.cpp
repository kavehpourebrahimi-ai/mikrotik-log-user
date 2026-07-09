#include "vms/client/ClientApp.hpp"

int main(int argc, char** argv) {
    const vms::client::ClientApp app;
    return app.run(argc, argv);
}
