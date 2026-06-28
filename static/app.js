// bubbles — single-page: tab switching + add magnet + progress polling

// ---- view switching (no page reload) --------------------------------------
const tabs = document.querySelectorAll(".nav-pill a");
const views = {
    add: document.getElementById("view-add"),
    downloading: document.getElementById("view-downloading"),
};
let pollTimer = null;

// view order defines slide direction: add(0) -> downloading(1)
const order = ["add", "downloading"];
let current = "add";

function showView(name) {
    if (!views[name]) name = "add";

    // going to a later tab slides right; earlier slides left
    const goingRight = order.indexOf(name) > order.indexOf(current);

    for (const tab of tabs) {
        tab.classList.toggle("active", tab.dataset.view === name);
    }

    for (const [key, el] of Object.entries(views)) {
        el.classList.remove("active", "to-left", "to-right");
        if (key === name) {
            // incoming view starts off-screen on the side it slides in from,
            // then .active animates it to center
            el.classList.add(goingRight ? "to-right" : "to-left");
            void el.offsetWidth;               // force reflow so the start pos applies
            el.classList.remove("to-left", "to-right");
            el.classList.add("active");
        } else {
            // outgoing view exits to the opposite side
            el.classList.add(goingRight ? "to-left" : "to-right");
        }
    }

    current = name;

    // only poll while the downloading view is visible
    if (name === "downloading") {
        poll();
        if (!pollTimer) pollTimer = setInterval(poll, 500);
    } else if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

tabs.forEach((tab) => {
    tab.addEventListener("click", (e) => {
        e.preventDefault();
        const name = tab.dataset.view;
        history.replaceState(null, "", "#" + name);
        showView(name);
    });
});

// deep-link / refresh support: honor #downloading in the URL
showView(location.hash.replace("#", "") || "add");

// ---- add magnet -----------------------------------------------------------
const form = document.getElementById("magnet-form");
const input = document.getElementById("magnet-input");
const status = document.getElementById("status");

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const magnet = input.value.trim();
    if (!magnet) return;

    status.textContent = "Adding…";
    try {
        const res = await fetch("/addMagnet", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ magnet }),
        });
        const data = await res.json();
        if (res.ok) {
            status.textContent = "Started download.";
            input.value = "";
        } else {
            status.textContent = "Error: " + (data.error || res.status);
        }
    } catch (err) {
        status.textContent = "Request failed: " + err.message;
    }
});

// ---- progress polling -----------------------------------------------------
const list = document.getElementById("download-list");

async function poll() {
    try {
        const res = await fetch("/progress");
        const data = await res.json();
        render(data);
    } catch (err) {
        console.error("progress poll failed", err);
    }
}

function render(data) {
    const ids = Object.keys(data);
    if (ids.length === 0) {
        list.innerHTML = '<li class="empty">No active downloads.</li>';
        return;
    }
    list.innerHTML = ids.map((id) => {
        const t = data[id];
        const pct = Math.round(t.percent ?? t.pct ?? 0);
        return `
            <li>
                <span class="name">${escapeHtml(t.name)} — ${escapeHtml(t.state)}</span>
                <div class="bar"><span style="width:${pct}%"></span></div>
            </li>
        `;
    }).join("");
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}
