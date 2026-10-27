// The frontend is served by Flask, so relative API paths work locally and after deployment.
const API = "";

const urlInput = document.querySelector("#media-url");
const previewButton = document.querySelector("#preview-btn");
const downloadButton = document.querySelector("#download-btn");
const errorBox = document.querySelector("#error-box");
const preview = document.querySelector("#preview");
const thumbnail = document.querySelector("#thumbnail");
const thumbnailPlaceholder = document.querySelector("#thumbnail-placeholder");
const progress = document.querySelector("#progress");
const progressText = document.querySelector("#progress-text");
const modeSelect = document.querySelector("#mode");
const qualitySelect = document.querySelector("#quality");

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}
function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}
function setBusy(busy, message = "Working on your request…") {
  previewButton.disabled = busy;
  downloadButton.disabled = busy;
  progress.hidden = !busy;
  progressText.textContent = busy ? message : "";
}
function currentUrl() {
  return urlInput.value.trim();
}

async function getVideoInfo(url) {
  const response = await fetch(`${API}/api/info`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url })
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

let previewTimer = null;
let lastPreviewedUrl = "";
let previewRequestId = 0;

function setThumbnail(src) {
  thumbnail.onerror = () => {
    thumbnail.hidden = true;
    thumbnailPlaceholder.hidden = false;
  };
  if (src) {
    thumbnail.src = src;
    thumbnail.hidden = false;
    thumbnailPlaceholder.hidden = true;
  } else {
    thumbnail.removeAttribute("src");
    thumbnail.hidden = true;
    thumbnailPlaceholder.hidden = false;
  }
}

async function previewCurrentUrl() {
  clearError();
  const url = currentUrl();
  if (!url) {
    preview.hidden = true;
    lastPreviewedUrl = "";
    setThumbnail("");
    return;
  }
  if (url === lastPreviewedUrl) return;

  const requestId = ++previewRequestId;
  setBusy(true, "Fetching media details…");
  try {
    const info = await getVideoInfo(url);
    if (requestId !== previewRequestId || url !== currentUrl()) return;
    document.querySelector("#media-title").textContent = info.title || "Untitled media";
    document.querySelector("#media-meta").textContent =
      `${info.uploader || "Unknown creator"}${info.duration ? " · " + formatDuration(info.duration) : ""} · ${info.site || "Media"}`;
    setThumbnail(info.thumbnail || "");
    preview.hidden = false;
    lastPreviewedUrl = url;
  } catch (error) {
    if (requestId === previewRequestId) {
      preview.hidden = true;
      showError(error.message || "Could not preview this media.");
    }
  } finally {
    if (requestId === previewRequestId) setBusy(false);
  }
}

previewButton.addEventListener("click", previewCurrentUrl);

// Automatically preview a complete pasted/typed URL, with a debounce to avoid excess requests.
urlInput.addEventListener("input", () => {
  clearError();
  lastPreviewedUrl = "";
  preview.hidden = true;
  setThumbnail("");
  if (previewTimer) clearTimeout(previewTimer);
  const url = currentUrl();
  if (!url) return;
  previewTimer = setTimeout(() => {
    try {
      const parsed = new URL(url);
      if (parsed.protocol === "https:") previewCurrentUrl();
    } catch (_) {
      // Wait until the input contains a complete URL.
    }
  }, 650);
});

downloadButton.addEventListener("click", async () => {
  clearError();
  const url = currentUrl();
  if (!url) return showError("Paste a YouTube or Instagram URL first.");

  setBusy(true, "Preparing your file. Large videos can take a while…");
  try {
    const response = await fetch(`${API}/api/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        quality: qualitySelect.value,
        mode: modeSelect.value
      })
    });

    const contentType = response.headers.get("content-type") || "";
    if (!response.ok || contentType.includes("application/json")) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Download failed.");
    }

    const blob = await response.blob();
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const originalFilename = match ? match[1] : "media-download";
    const safeFilename = originalFilename.replace(/[^a-zA-Z0-9._-]/g, "_");
    const filename = safeFilename.toLowerCase().startsWith("zdownload")
      ? safeFilename
      : `zdownload-${safeFilename}`;
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 30000);
  } catch (error) {
    showError(error.message || "Download failed. Please try again.");
  } finally {
    setBusy(false);
  }
});

function formatDuration(seconds) {
  const s = Math.max(0, Number(seconds) || 0);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = Math.floor(s % 60);
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}` : `${m}:${String(r).padStart(2, "0")}`;
}

urlInput.addEventListener("keydown", event => {
  if (event.key === "Enter") previewButton.click();
});
modeSelect.addEventListener("change", () => {
  qualitySelect.disabled = modeSelect.value === "audio";
});
qualitySelect.disabled = modeSelect.value === "audio";
