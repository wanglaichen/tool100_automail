const state = {
    mailboxes: [],
    selectedMailboxId: null,
    selectedEmailId: null,
    emailsByMailbox: {},
    autoRefresh: false,
    timerId: null,
};

function byId(id) {
    return document.getElementById(id);
}

function showMessage(kind, text) {
    const errorBox = byId("errorBox");
    const successBox = byId("successBox");
    errorBox.classList.add("d-none");
    successBox.classList.add("d-none");

    const box = kind === "error" ? errorBox : successBox;
    box.textContent = text;
    box.classList.remove("d-none");
}

function clearMessages() {
    byId("errorBox").classList.add("d-none");
    byId("successBox").classList.add("d-none");
}

async function requestJson(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.message || data.error || "请求失败");
    }
    return data;
}

function formatTime(value) {
    if (!value) {
        return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString("zh-CN", { hour12: false });
}

function renderSummary(summary) {
    byId("mailboxCount").textContent = summary.mailbox_count ?? 0;
    byId("createdMailboxCount").textContent = summary.created_mailbox_count ?? 0;
    byId("emailCount").textContent = summary.email_count ?? 0;
    byId("lastMailboxCreatedAt").textContent = formatTime(summary.last_mailbox_created_at);
    byId("lastSyncAt").textContent = formatTime(summary.last_sync_at);
}

function renderMailboxes(items) {
    state.mailboxes = items;
    const tbody = byId("mailboxTableBody");
    tbody.innerHTML = "";

    if (!items.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-cell">暂无邮箱</td></tr>';
        return;
    }

    items.forEach((item) => {
        const tr = document.createElement("tr");
        if (item.id === state.selectedMailboxId) {
            tr.classList.add("row-active");
        }

        tr.innerHTML = `
            <td>
                <div class="mailbox-address">${item.email_address}</div>
                <div class="mailbox-meta">${escapeHtml(item.domain || "")} · 最近邮件: ${formatTime(item.latest_email_at)}</div>
            </td>
            <td>${item.email_count}</td>
            <td>${formatTime(item.created_at)}</td>
            <td><button class="btn btn-sm btn-outline-info">查看邮件</button></td>
        `;

        tr.querySelector("button").addEventListener("click", () => {
            selectMailbox(item.id);
        });

        tbody.appendChild(tr);
    });
}

function renderEmailList(mailboxId) {
    const items = state.emailsByMailbox[mailboxId] || [];
    const list = byId("emailList");

    if (!items.length) {
        list.innerHTML = '<div class="empty-state">当前邮箱暂无邮件</div>';
        return;
    }

    list.innerHTML = "";
    items.forEach((item) => {
        const button = document.createElement("button");
        button.className = "email-item";
        if (item.email_id === state.selectedEmailId) {
            button.classList.add("active");
        }
        button.innerHTML = `
            <strong>${escapeHtml(item.subject || "(无主题)")}</strong>
            <span>${escapeHtml(item.from_address || "")}</span>
            <small>${formatTime(item.created_at)}</small>
        `;
        button.addEventListener("click", () => selectEmail(item.email_id));
        list.appendChild(button);
    });
}

function renderEmailDetail(email) {
    const panel = byId("emailDetail");
    const htmlContent = String(email.html || email.body || "");
    const isHtml = /<\/?[a-z][\s\S]*>/i.test(htmlContent);
    const textContent = email.text_excerpt || email.body_excerpt || email.body || "";

    panel.innerHTML = `
        <div class="detail-head">
            <h3>${escapeHtml(email.subject || "(无主题)")}</h3>
            <div class="detail-meta">
                <span>发件人: ${escapeHtml(email.from_address || "")}</span>
                <span>时间: ${formatTime(email.created_at)}</span>
            </div>
        </div>
        <div class="detail-section">
            <label>收件人</label>
            <div>${escapeHtml((email.to || []).join(", ")) || "-"}</div>
        </div>
        <div class="detail-section">
            <label>正文预览</label>
            ${
                isHtml
                    ? `
                        <div class="email-html-shell">
                            <iframe
                                class="email-html-frame"
                                sandbox="allow-popups allow-popups-to-escape-sandbox"
                                referrerpolicy="no-referrer"
                                srcdoc="${escapeHtml(buildHtmlPreview(htmlContent))}"
                            ></iframe>
                        </div>
                    `
                    : `<pre>${escapeHtml(textContent)}</pre>`
            }
        </div>
        ${
            isHtml && textContent
                ? `
                    <div class="detail-section">
                        <label>纯文本</label>
                        <pre>${escapeHtml(textContent)}</pre>
                    </div>
                `
                : ""
        }
        ${
            isHtml
                ? `
                    <div class="detail-section">
                        <label>HTML 源码</label>
                        <pre>${escapeHtml(htmlContent)}</pre>
                    </div>
                `
                : ""
        }
    `;
}

function buildHtmlPreview(htmlContent) {
    return `<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <base target="_blank">
    <style>
        body {
            margin: 0;
            padding: 16px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
            color: #1f2937;
            background: #fff;
            line-height: 1.6;
            word-break: break-word;
        }
        img { max-width: 100%; height: auto; }
        table { max-width: 100%; }
        a { color: #0f766e; }
    </style>
</head>
<body>${htmlContent}</body>
</html>`;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

async function loadSummary() {
    const data = await requestJson("/api/summary");
    renderSummary(data);
}

async function loadMailboxes(refresh = false) {
    const data = await requestJson(`/api/mailboxes${refresh ? "?refresh=1" : ""}`);
    renderMailboxes(data.items || []);

    if (state.selectedMailboxId) {
        const exists = (data.items || []).some((item) => item.id === state.selectedMailboxId);
        if (!exists) {
            state.selectedMailboxId = null;
            state.selectedEmailId = null;
            byId("activeMailboxLabel").textContent = "未选择邮箱";
            byId("emailList").innerHTML = '<div class="empty-state">选择左侧邮箱后查看邮件</div>';
            byId("emailDetail").innerHTML = '<div class="empty-state">点击邮件后查看详情</div>';
        }
    }
}

async function selectMailbox(mailboxId) {
    try {
        clearMessages();
        state.selectedMailboxId = mailboxId;
        state.selectedEmailId = null;
        const mailbox = state.mailboxes.find((item) => item.id === mailboxId);
        byId("activeMailboxLabel").textContent = mailbox ? mailbox.email_address : "未选择邮箱";
        byId("emailList").innerHTML = '<div class="empty-state">正在同步邮件...</div>';
        byId("emailDetail").innerHTML = '<div class="empty-state">请选择一封邮件</div>';

        renderMailboxes(state.mailboxes);
        await loadEmails(mailboxId, true);
        await loadMailboxes(false);
        await loadSummary();
    } catch (error) {
        showMessage("error", error.message);
    }
}

async function loadEmails(mailboxId, refresh = false) {
    const data = await requestJson(`/api/mailboxes/${mailboxId}/emails${refresh ? "?refresh=1" : ""}`);
    state.emailsByMailbox[mailboxId] = data.items || [];
    renderEmailList(mailboxId);

    if ((data.items || []).length) {
        await selectEmail((data.items || [])[0].email_id);
    } else {
        byId("emailDetail").innerHTML = '<div class="empty-state">当前邮箱暂无邮件</div>';
    }
}

async function selectEmail(emailId) {
    try {
        state.selectedEmailId = emailId;
        renderEmailList(state.selectedMailboxId);
        const email = await requestJson(`/api/emails/${emailId}`);
        renderEmailDetail(email);
    } catch (error) {
        showMessage("error", error.message);
    }
}

async function createMailboxes() {
    clearMessages();
    const count = Number(byId("createCount").value || 0);
    if (!Number.isInteger(count) || count < 1 || count > 50) {
        showMessage("error", "注册数量必须是 1 到 50 的整数");
        return;
    }

    const domainOption = byId("domainOption").value || "zazamail.link";
    if (!domainOption) {
        showMessage("error", "请选择邮箱后缀");
        return;
    }

    byId("createButton").disabled = true;
    try {
        const result = await requestJson("/api/mailboxes", {
            method: "POST",
            body: JSON.stringify({ count, domain_option: domainOption }),
        });
        showMessage("success", result.message || "邮箱创建完成");
        renderSummary(result.summary || {});
        await loadMailboxes(false);
    } catch (error) {
        showMessage("error", error.message);
    } finally {
        byId("createButton").disabled = false;
    }
}

async function syncProviderMailboxes() {
    clearMessages();
    const button = byId("syncProviderButton");
    button.disabled = true;
    try {
        const result = await requestJson("/api/mailboxes/sync", {
            method: "POST",
            body: JSON.stringify({}),
        });
        showMessage("success", result.message || "平台邮箱同步完成");
        renderSummary(result.summary || {});
        renderMailboxes(result.items || []);
    } catch (error) {
        showMessage("error", error.message);
    } finally {
        button.disabled = false;
    }
}

function syncAutoRefreshButton() {
    byId("toggleAutoRefreshButton").textContent = `自动刷新: ${state.autoRefresh ? "开" : "关"}`;
}

async function refreshAll() {
    try {
        clearMessages();
        await loadMailboxes(true);
        await loadSummary();
        if (state.selectedMailboxId) {
            await loadEmails(state.selectedMailboxId, true);
        }
    } catch (error) {
        showMessage("error", error.message);
    }
}

function toggleAutoRefresh() {
    state.autoRefresh = !state.autoRefresh;
    syncAutoRefreshButton();

    if (state.autoRefresh) {
        state.timerId = window.setInterval(refreshAll, window.APP_CONFIG.pollIntervalMs);
    } else if (state.timerId) {
        window.clearInterval(state.timerId);
        state.timerId = null;
    }
}

async function boot() {
    byId("createButton").addEventListener("click", createMailboxes);
    byId("syncProviderButton").addEventListener("click", syncProviderMailboxes);
    byId("refreshMailboxesButton").addEventListener("click", refreshAll);
    byId("toggleAutoRefreshButton").addEventListener("click", toggleAutoRefresh);
    syncAutoRefreshButton();

    try {
        await loadSummary();
        await loadMailboxes(false);
    } catch (error) {
        showMessage("error", error.message);
    }
}

document.addEventListener("DOMContentLoaded", boot);
