import { BASE_URL, downloadURI, get, post } from "./helpers";

let lastYtThumbnail = null;
let isBusy = false;

function populateForm(json) {
    const mostLikelyArtist =
        json["artists"].length > 0 ? json["artists"][0][0].name : "";

    const nameSuggestions = [];

    for (const artistAndScore of json["artists"]) {
        const artist = artistAndScore[0];
        nameSuggestions.push(artist.name);
        artist["alternative_names"].forEach((n) => nameSuggestions.push(n));
    }

    const suggestionsDiv = document.getElementById("artist-suggestions");

    // un-hide
    document
        .getElementById("artist-suggestions-div")
        .classList.remove("visually-hidden");

    // remove any existing suggestions
    suggestionsDiv.innerHTML = "";

    for (let i = 0; i < nameSuggestions.length; i++) {
        const name = nameSuggestions[i];

        const suggestionLink = document.createElement("span");
        suggestionLink.classList.add("suggestion-link");
        suggestionLink.innerText = name;

        suggestionLink.onclick = () => {
            document.getElementById("artist-tag").value = name;
        };
        suggestionsDiv.appendChild(suggestionLink);

        if (i < nameSuggestions.length - 1) {
            suggestionsDiv.append(", ");
        }
    }

    if (nameSuggestions.length === 0) {
        suggestionsDiv.innerText = "Could not guess artist :(";
    }

    document.getElementById("title-tag").value = json["title"];
    document.getElementById("artist-tag").value = mostLikelyArtist;
    document.getElementById("album-tag").value = json["album"];
    document.getElementById("youtube-id").value = json["video_id"];
    lastYtThumbnail = json["thumbnail_url"];
    document.getElementById("cover-tag").value = lastYtThumbnail;
    document
        .getElementById("cover-preview-img")
        .setAttribute("src", lastYtThumbnail);
}

function trackStatus(request_id) {
    let urlCopy = new URL(BASE_URL.toString());
    if (BASE_URL.protocol === "http:") {
        urlCopy.protocol = "ws:";
    } else {
        urlCopy.protocol = "wss:";
    }

    const ws = new WebSocket(`${urlCopy}/status/ws/${request_id}`);
    const formSpinner = document.getElementById("download-form-spinner");
    const downloadButton = document.getElementById("download-form-button");
    const downloadButtonText = document.getElementById(
        "download-form-button-text"
    );
    const progressBar = document.getElementById("download-progress-bar");

    formSpinner.hidden = false;
    downloadButton.disabled = true;

    ws.addEventListener("message", function (event) {
        const jobStatus = JSON.parse(event.data);
        const status = jobStatus["status"];
        const percentageDone = Math.round(jobStatus["percentage_done"] * 100);
        downloadButtonText.innerText =
            status.charAt(0).toUpperCase() + status.slice(1);
        progressBar.innerText = `${percentageDone}%`;

        switch (status) {
            case "done":
                formSpinner.hidden = true;
                downloadButton.disabled = false;
                updateSongTable();
                isBusy = false;
                break;

            case "downloading":
                downloadButtonText.innerText = "Downloading video";
                progressBar.style.width = `${percentageDone}%`;
                break;

            case "converting":
                downloadButtonText.innerText = "Extracting audio";
                break;

            case "error":
                formSpinner.hidden = true;
                downloadButton.disabled = false;
                isBusy = false;
                break;
        }
    });

    ws.addEventListener("close", (_) => (isBusy = false));
    ws.addEventListener("error", (_) => (isBusy = false));
}

function updateSongTable() {
    get("/songs")
        .then((response) => response.json())
        .then((json) => {
            const songTable = document.getElementById("song-table");

            // XXX: Force clear table
            songTable.innerHTML = "";

            for (const song of json) {
                const row = songTable.insertRow();
                row.setAttribute("data-song-id", song.id);

                // XXX: Add Z as the given time is in UTC
                row.insertCell().innerText = song.title;
                row.insertCell().innerText = song.artists
                    .map((a) => a["name"])
                    .join(",");
                row.insertCell().innerText = song.album["name"];
                const downloadCell = row.insertCell();
                row.insertCell().innerText = new Date(
                    `${song["created_date"]}Z`
                ).toLocaleString();
                row.insertCell().innerText =
                    song.tagger === null ? "-" : song.tagger.name;

                const downloadButton = document.createElement("button");
                downloadButton.innerText = "Download";
                downloadButton.classList.add("btn");
                downloadButton.classList.add("btn-primary");
                downloadButton.classList.add("btn-sm");
                downloadButton.addEventListener("click", () => {
                    downloadURI(BASE_URL + `/download/${song.id}`);
                });
                downloadCell.appendChild(downloadButton);
            }
        })
        .catch((error) => console.error("Error:", error));
}

const inputForm = document.getElementById("input-form");
inputForm.addEventListener("submit", (ev) => {
    ev.preventDefault();

    // Check if download is not busy
    if (isBusy) {
        console.log("Wait until finished");
        return;
    }

    const videoIdInput = document.getElementById("youtube-form-link").value;

    if (videoIdInput === "") {
        return;
    }

    // Get youtube video ID
    const url = new URL(videoIdInput);
    const videoId = url.searchParams.get("v");

    if (videoId === null) {
        alert("Provided URL is invalid: it does not contain a video ID");
        return;
    }

    post("/metadata", { video_id: videoId })
        .then((response) => response.json())
        .then((json) => populateForm(json))
        .catch((error) => console.error("Error:", error));
});

const tagForm = document.getElementById("tag-form");
tagForm.addEventListener("submit", (ev) => {
    ev.preventDefault();

    const dlRequest = {
        title: document.getElementById("title-tag").value,
        artists: document.getElementById("artist-tag").value.split(","),
        album: document.getElementById("album-tag").value,
        original_artists: [],
        tagger: document.getElementById("tagger-tag").value,
        video_id: document.getElementById("youtube-id").value,
        thumbnail_url: lastYtThumbnail,
    };

    isBusy = true;
    post("/convert", dlRequest)
        .then((response) => response.json())
        .then((json) => trackStatus(json["request_id"]))
        .catch((error) => {
            console.error("Error:", error);
            isBusy = false;
        });
});

window.addEventListener(
    "DOMContentLoaded",
    function () {
        // Fetch all the forms we want to apply custom Bootstrap validation styles to
        const forms = document.getElementsByClassName("needs-validation");
        // Loop over them and prevent submission
        Array.prototype.filter.call(forms, (form) => {
            form.addEventListener(
                "submit",
                (event) => {
                    if (form.checkValidity() === false) {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                    form.classList.add("was-validated");
                },
                false
            );
        });

        for (const e of document.getElementsByClassName("date-convert")) {
            e.innerHTML = new Date(
                parseFloat(e.innerHTML) * 1000
            ).toLocaleString();
            e.style.visibility = "visible";
        }

        window.download = downloadURI;
    },
    false
);
