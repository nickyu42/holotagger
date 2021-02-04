'use strict';

import {BASE_URL, downloadURI, get, post} from "./helpers";

let lastYtThumbnail = null;
let lastThumbnail = null;
let isBusy = false;

function populateForm(json) {
    document.getElementById('title-tag').value = json['title'];
    document.getElementById('artist-tag').value = json['artists'].join(',');
    document.getElementById('album-tag').value = json['album'];
    document.getElementById('youtube-id').value = json['video_id'];

    if (json['artists'].length > 0) {
        getCoverURI(json['artists'][0]).then(r => {
            if (r === null) {
                lastThumbnail = null;
            } else {
                lastThumbnail = new URL(`/cover/${r}`, BASE_URL);
            }
        })
    }

    lastYtThumbnail = json['thumbnail_url'];
    document.getElementById('cover-tag').value = lastThumbnail;
    document.getElementById('cover-preview-img').setAttribute('src', lastThumbnail);
}

async function getCoverURI(artistName) {
    const response = await get(`/search/artist?name=${artistName}`)

    if (response.status === 200) {
        return (await response.json())['id']
    }

    return null;
}

function trackStatus(request_id) {
    const ws = new WebSocket(`ws://${API_HOST}/status/ws/${request_id}`);
    const formSpinner = document.getElementById('download-form-spinner');
    const downloadButton = document.getElementById('download-form-button');

    formSpinner.hidden = false;
    downloadButton.disabled = true;

    ws.addEventListener('message', function (event) {
        const status = JSON.parse(event.data)['status'];
        downloadButton.innerText = status.charAt(0).toUpperCase() + status.slice(1);
        switch (status) {
            case 'done':
                formSpinner.hidden = true;
                downloadButton.disabled = false;
                updateSongTable();
                isBusy = false;
                break;

            case 'downloading':
                downloadButton.innerText = 'Converting';
                break;

            case 'error':
                formSpinner.hidden = true;
                downloadButton.disabled = false;
                isBusy = false;
                break
        }
    });

    ws.addEventListener('close', _ => isBusy = false);
    ws.addEventListener('error', _ => isBusy = false);
}

function updateSongTable() {
    get('/songs')
        .then(response => response.json())
        .then(json => {
            const songTable = document.getElementById('song-table');

            // XXX: Force clear table
            songTable.innerHTML = '';

            for (const song of json) {
                const row = songTable.insertRow();
                row.setAttribute('data-song-id', song.id);

                // XXX: Add Z as the given time is in UTC
                row.insertCell().innerText = song.title;
                row.insertCell().innerText = song.artists.join(',');
                row.insertCell().innerText = song.album;
                const downloadCell = row.insertCell();
                row.insertCell().innerText = new Date(`${song['created_date']}Z`).toLocaleString();
                row.insertCell().innerText = song.tagger === null ? '-' : song.tagger;

                const downloadButton = document.createElement('button');
                downloadButton.innerText = 'Download';
                downloadButton.classList.add('btn');
                downloadButton.classList.add('btn-primary');
                downloadButton.classList.add('btn-sm');
                downloadButton.addEventListener('click', () => {
                    downloadURI(new URL(`/download/${song.id}`, BASE_URL).toString());
                });
                downloadCell.appendChild(downloadButton);
            }
        })
        .catch((error) => console.error('Error:', error));
}

const inputForm = document.getElementById('input-form');
inputForm.addEventListener('submit', ev => {
    ev.preventDefault();

    // Check if download is not busy
    if (isBusy) {
        console.log("Wait until finished");
        return;
    }

    const videoIdInput = document.getElementById('youtube-form-link').value;

    if (videoIdInput === "") {
        return;
    }

    // Get youtube video ID
    const url = new URL(videoIdInput);
    const videoId = url.searchParams.get('v');

    if (videoId === null) {
        alert('Provided URL is invalid: it does not contain a video ID');
        return;
    }

    post('/metadata', {video_id: videoId})
        .then(response => response.json())
        .then(json => populateForm(json))
        .catch((error) => console.error('Error:', error));
});

const tagForm = document.getElementById('tag-form');
tagForm.addEventListener('submit', ev => {
    ev.preventDefault();

    const dlRequest = {
        'title': document.getElementById('title-tag').value,
        'artists': document.getElementById('artist-tag').value.split(','),
        'album': document.getElementById('album-tag').value,
        'original_artists': [],
        'tagger': document.getElementById('tagger-tag').value,
        'video_id': document.getElementById('youtube-id').value
    };

    isBusy = true;
    post('/convert', dlRequest)
        .then(response => response.json())
        .then(json => trackStatus(json['request_id']))
        .catch((error) => {
            console.error('Error:', error);
            isBusy = false;
        });
});

window.addEventListener('DOMContentLoaded', function () {
    // Fetch all the forms we want to apply custom Bootstrap validation styles to
    const forms = document.getElementsByClassName('needs-validation');
    // Loop over them and prevent submission
    Array.prototype.filter.call(forms, form => {
        form.addEventListener('submit', event => {
            if (form.checkValidity() === false) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    for (const e of document.getElementsByClassName('date-convert')) {
        e.innerHTML = new Date(parseFloat(e.innerHTML) * 1000).toLocaleString();
        e.style.visibility = 'visible';
    }
}, false);

