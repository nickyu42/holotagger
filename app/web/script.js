'use strict';

const API_HOST = 'localhost'
let lastThumbnail = null;
let isBusy = false;

function downloadURI(uri) {
    const link = document.createElement("a");
    link.href = uri;
    document.body.appendChild(link);
    link.click();
    link.remove();
}

function populateForm(json) {
    document.getElementById('title-tag').value = json['title'];
    document.getElementById('artist-tag').value = json['artists'].join(',');
    document.getElementById('album-tag').value = json['album'];
    document.getElementById('youtube-id').value = json['video_id'];

    // TODO: make it possible to choose
    lastThumbnail = json['thumbnail_url'];
    document.getElementById('cover-tag').value = lastThumbnail;
    document.getElementById('cover-preview-img').setAttribute('src', lastThumbnail);
}

function getCoverURI(artistName) {
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
    fetch(`http://${API_HOST}/songs`, {
        method: 'GET',
        mode: 'cors',
        cache: 'no-cache',
        headers: {
            'Content-Type': 'application/json'
        },
        redirect: 'follow',
        referrerPolicy: 'no-referrer',
    })
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
                    downloadURI(`http://${API_HOST}/download/${song.id}`);
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

    fetch(`http://${API_HOST}/metadata`, {
        method: 'POST',
        mode: 'cors',
        cache: 'no-cache',
        headers: {
            'Content-Type': 'application/json'
        },
        redirect: 'follow',
        referrerPolicy: 'no-referrer',
        body: JSON.stringify({video_id: videoId}),
    })
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
    fetch(`http://${API_HOST}/convert`, {
        method: 'POST',
        mode: 'cors',
        cache: 'no-cache',
        headers: {
            'Content-Type': 'application/json'
        },
        redirect: 'follow',
        referrerPolicy: 'no-referrer',
        body: JSON.stringify(dlRequest),
    })
        .then(response => response.json())
        .then(json => trackStatus(json['request_id']))
        .catch((error) => {
            console.error('Error:', error);
            isBusy = false;
        });
});

window.addEventListener('load', function() {
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

    // Check if backend is available
    fetch(`http://${API_HOST}/`, {
        mode: 'cors',
        cache: 'no-cache',
        redirect: 'follow',
        referrerPolicy: 'no-referrer',
    })
        .then(response => {
            if (response.status !== 200) {
                document.getElementById('status-alert').hidden = false;
            } else {
                updateSongTable();
            }
        })
        .catch(_ => {
            document.getElementById('status-alert').hidden = false;
        });
}, false);