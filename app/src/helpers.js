/**
 * Base URL for all requests.
 * @type {URL}
 */
export const BASE_URL = new URL(document.querySelector("meta[name='api_url']").getAttribute('content'), window.location.origin);

/**
 * Helper for GET requests.
 * @param {string} url - relative url of the form example/path/
 * @returns {Promise<Response>}
 */
export function get(url) {
    return fetch(BASE_URL + url, {
        method: 'GET',
        mode: 'cors',
        cache: 'no-cache',
        headers: {
            'Content-Type': 'application/json'
        },
        redirect: 'follow',
        referrerPolicy: 'no-referrer',
    });
}

/**
 * Helper for POST requests.
 * @param {string} url - relative url of the form example/path/
 * @param {object} body
 * @returns {Promise<Response>}
 */
export function post(url, body) {
    return fetch(BASE_URL + url, {
        method: 'POST',
        mode: 'cors',
        cache: 'no-cache',
        headers: {
            'Content-Type': 'application/json'
        },
        redirect: 'follow',
        referrerPolicy: 'no-referrer',
        body: JSON.stringify(body),
    });
}

/**
 * Downloads a file from the given uri.
 * @param {string} uri
 */
export function downloadURI(uri) {
    const link = document.createElement("a");
    link.href = uri;
    document.body.appendChild(link);
    link.click();
    link.remove();
}
