let isBusy = false;

function populateForm(json) {
    document.getElementById('title-tag').value = json['title'];
    document.getElementById('artist-tag').value = json['artists'].join(',');
    document.getElementById('album-tag').value = json['album'];
    document.getElementById('youtube-id').value = json['video_id'];
}

function trackStatus(request_id) {
    const ws = new WebSocket(`ws://localhost/status/ws/${request_id}`);
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
                break;

            case 'downloading':
                downloadButton.innerText = 'Converting';
                break;

            case 'error':
                formSpinner.hidden = true;
                downloadButton.disabled = false;
                break
        }
    });
}

function updateSongTable() {
    fetch('http://localhost/songs', {
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
            
            for (const song of json) {
                const row = songTable.insertRow();
                row.setAttribute('data-song-id', song.id);
                row.insertCell().innerText = '';
                row.insertCell().innerText = song.title;
                row.insertCell().innerText = song.artists.join(',');
                row.insertCell().innerText = song.album;
                const downloadCell = row.insertCell();

                const downloadButton = document.createElement('button');
                downloadButton.innerText = 'Download';
                downloadButton.classList.add('btn');
                downloadButton.classList.add('btn-primary');
                downloadButton.classList.add('btn-sm');
                downloadCell.appendChild(downloadButton)
            }
        })
        .catch((error) => console.error('Error:', error));
}

inputForm = document.getElementById('input-form');
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

    fetch('http://localhost/metadata', {
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

tagForm = document.getElementById('tag-form');
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

    fetch('http://localhost/download', {
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
        .catch((error) => console.error('Error:', error));
});

// Check if backend is available
fetch('http://localhost/', {
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
