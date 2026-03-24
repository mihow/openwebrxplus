import json
from owrx.controllers import Controller
from owrx.controllers.template import TemplateController


class ScannerPageController(TemplateController):
    """GET /scanner — serves the mobile scanner UI."""
    def indexAction(self):
        self.serve_template("scanner.html")


class ScannerApiController(Controller):
    """GET /api/scanner — scanner state."""
    def indexAction(self):
        from owrx.scanner import ScannerService
        service = ScannerService.get_instance()
        self.send_response(
            json.dumps(service.state.to_dict()),
            content_type="application/json",
        )


class ScannerDetectionsController(Controller):
    """GET /api/scanner/detections — recent detections."""
    def indexAction(self):
        from owrx.scanner import ScannerService
        service = ScannerService.get_instance()
        if service.db is None:
            self.send_response(json.dumps([]), content_type="application/json")
            return
        limit = 50
        if hasattr(self.request, 'query') and "limit" in self.request.query:
            try:
                limit = int(self.request.query["limit"][0])
            except (ValueError, IndexError):
                pass
        detections = service.db.get_recent_detections(limit=limit)
        self.send_response(
            json.dumps({"detections": detections}),
            content_type="application/json",
        )


class ScannerActiveController(Controller):
    """GET /api/scanner/active — most active frequencies."""
    def indexAction(self):
        from owrx.scanner import ScannerService
        service = ScannerService.get_instance()
        if service.db is None:
            self.send_response(json.dumps([]), content_type="application/json")
            return
        hours = 24
        if hasattr(self.request, 'query') and "hours" in self.request.query:
            try:
                hours = int(self.request.query["hours"][0])
            except (ValueError, IndexError):
                pass
        active = service.db.get_most_active(hours=hours)
        self.send_response(
            json.dumps({"signals": active}),
            content_type="application/json",
        )


class ScannerBookmarksController(Controller):
    """GET /api/scanner/bookmarks — all scanner bookmarks."""
    def indexAction(self):
        from owrx.scanner import ScannerService
        service = ScannerService.get_instance()
        if service.db is None:
            self.send_response(json.dumps([]), content_type="application/json")
            return
        bookmarks = service.db.get_all_bookmarks()
        self.send_response(
            json.dumps({"bookmarks": bookmarks}),
            content_type="application/json",
        )


class ScannerCommandController(Controller):
    """POST /api/scanner/command — send command to scanner."""
    def indexAction(self):
        from owrx.scanner import ScannerService
        service = ScannerService.get_instance()
        try:
            body = json.loads(self.get_body().decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_response(
                json.dumps({"error": "invalid JSON"}),
                content_type="application/json",
            )
            return

        command = body.get("command")
        params = body.get("params", {})
        if command == "start":
            service.start()
        elif command == "stop":
            service.stop()
        elif command == "pause":
            service.pause()
        elif command == "resume":
            service.resume()
        elif command == "skip":
            service.skip()
        elif command == "hold":
            service.hold(params.get("frequency") or body.get("frequency"))
        elif command == "tune":
            service.hold(params.get("frequency"))
        else:
            self.send_response(
                json.dumps({"error": "unknown command: {}".format(command)}),
                content_type="application/json",
            )
            return

        self.send_response(
            json.dumps(service.state.to_dict()),
            content_type="application/json",
        )
