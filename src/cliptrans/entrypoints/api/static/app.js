/* YouTube IFrame API */

var ytPlayer = null;

function onYouTubeIframeAPIReady() {
  var wrapper = document.getElementById("yt-player-wrapper");
  if (!wrapper) return;

  ytPlayer = new YT.Player("yt-player", {
    videoId: typeof YT_VIDEO_ID !== "undefined" ? YT_VIDEO_ID : "",
    playerVars: { playsinline: 1 },
    events: {
      onReady: function(e) { e.target.pauseVideo(); },
    },
  });
}

function loadYTApi() {
  if (document.getElementById("yt-player-wrapper") == null) return;
  var tag = document.createElement("script");
  tag.src = "https://www.youtube.com/iframe_api";
  var firstScriptTag = document.getElementsByTagName("script")[0];
  firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
}

function seekTo(seconds) {
  seconds = parseFloat(seconds);
  if (!ytPlayer || typeof ytPlayer.seekTo !== "function") {
    console.warn("YouTube player not ready");
    return;
  }
  ytPlayer.seekTo(seconds, true);
  ytPlayer.playVideo();
}

function syncClipCounts() {
  var candidateLabel = document.getElementById("candidate-count-label");
  var selectionLabel = document.getElementById("selection-count-label");
  var candidateCount = document.querySelectorAll("#candidates-list .clip-card").length;
  var selectionCount = document.querySelectorAll("#selections-list .clip-card").length;

  if (candidateLabel) candidateLabel.textContent = "Candidates (" + candidateCount + ")";
  if (selectionLabel) selectionLabel.textContent = "Selections (" + selectionCount + ")";
}

/* Init */
document.addEventListener("DOMContentLoaded", function () {
  loadYTApi();
  syncClipCounts();
});

document.body.addEventListener("htmx:afterSettle", function () {
  syncClipCounts();
});
