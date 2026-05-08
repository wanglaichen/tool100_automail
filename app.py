from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from config import AppConfig
from services.mailbox_service import MailboxService


app = Flask(__name__)
app.config.from_object(AppConfig)

mailbox_service = MailboxService.from_app_config(app.config)


@app.errorhandler(ValueError)
def handle_value_error(error):
    return jsonify({"message": str(error)}), 400


@app.errorhandler(HTTPException)
def handle_http_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"message": error.description}), error.code
    return error


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    app.logger.exception("Unhandled error")
    if request.path.startswith("/api/"):
        return jsonify({"message": str(error)}), 500
    raise error


@app.route("/")
def index():
    return render_template(
        "index.html",
        provider=app.config["MAIL_PROVIDER"],
        poll_interval_ms=app.config["MAIL_POLL_INTERVAL_MS"],
    )


@app.route("/api/summary", methods=["GET"])
def summary():
    return jsonify(mailbox_service.get_summary())


@app.route("/api/mailboxes", methods=["GET"])
def list_mailboxes():
    refresh = request.args.get("refresh") == "1"
    return jsonify({"items": mailbox_service.list_mailboxes(refresh=refresh)})


@app.route("/api/mailboxes", methods=["POST"])
def create_mailboxes():
    payload = request.get_json(silent=True) or {}
    count = payload.get("count", 1)
    domain_option = payload.get("domain_option", "default")
    created = mailbox_service.create_mailboxes(count, domain_option=domain_option)
    return jsonify(
        {
            "message": f"已创建 {len(created)} 个邮箱",
            "items": created,
            "summary": mailbox_service.get_summary(),
        }
    )


@app.route("/api/mailboxes/sync", methods=["POST"])
def sync_mailboxes():
    result = mailbox_service.sync_provider_mailboxes()
    return jsonify(
        {
            "message": f"已同步平台邮箱：新增 {result['imported']} 个，更新 {result['updated']} 个",
            "result": result,
            "items": mailbox_service.list_mailboxes(refresh=False),
            "summary": mailbox_service.get_summary(),
        }
    )


@app.route("/api/mailboxes/<mailbox_id>/emails", methods=["GET"])
def list_emails(mailbox_id: str):
    refresh = request.args.get("refresh") == "1"
    return jsonify({"items": mailbox_service.list_emails(mailbox_id, refresh=refresh)})


@app.route("/api/emails/<email_id>", methods=["GET"])
def get_email(email_id: str):
    return jsonify(mailbox_service.get_email(email_id))


if __name__ == "__main__":
    app.run(debug=True, host=app.config["APP_HOST"], port=app.config["APP_PORT"])
