let isBusy = false;

function populateForm(json) {
    document.getElementById('title-tag').value = json['title'];
    document.getElementById('artist-tag').value = json['artists'].join(',');
    document.getElementById('album-tag').value = json['album'];
    document.getElementById('youtube-id').value = json['video_id'];
}

function track_status(request_id) {
    const ws = new WebSocket(`ws://localhost/status/${request_id}`);

    const progressBar = document.getElementById('download-progress-bar');
    progressBar.setAttribute('aria-valuenow', '0');

    ws.addEventListener('message', function (event) {
        const d = JSON.parse(event.data);

        switch (d['status']) {
            case 'waiting':
                progressBar.innerText = 'Waiting';
                break;

            case 'downloading':
                const p = String(d['percentage']);
                progressBar.innerText = 'Downloading';
                progressBar.setAttribute('aria-valuenow', p);
                progressBar.setAttribute('style', `width: ${p}%`);
                break;

            case 'done':
                progressBar.innerText = 'Done';
                progressBar.setAttribute('aria-valuenow', '100');
                progressBar.setAttribute('style', `width: 100%`);
                break;

            case 'error':
                progressBar.innerText = 'Error';
                console.error('Error occurred during downloading');
                break
        }
    });
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
        .catch((error) => {
            console.error('Error:', error);
        });
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
        .then(json => track_status(json['request_id']))
        .catch((error) => {
            console.error('Error:', error);
        });
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
        }
    })
    .catch(_ => {
        document.getElementById('status-alert').hidden = false;
    });



