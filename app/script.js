let isBusy = false;

function populateForm(raw) {
    const json = JSON.parse(raw);
    document.getElementById('title-tag').value = json['title'];
    document.getElementById('artist-tag').value = json['artists'].join(',');
    document.getElementById('album-tag').value = json['album'];
    document.getElementById('youtube-link').value = document.getElementById('youtube-form-link').value;
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



