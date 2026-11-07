// Test-only transport substitution, loaded into the disposable upstream server.
// A real Discord webhook is NEVER redirected. No production code imports this file.
const path = require('node:path');
const { createRequire } = require('node:module');
const upstreamRequire = createRequire(path.join(process.cwd(), 'package.json'));
const axios = upstreamRequire('axios');
const fake = 'https://discord.com/api/webhooks/KUMAOPS_TEST/NOT_A_REAL_TOKEN';
const originalGet = axios.get.bind(axios);
const originalPost = axios.post.bind(axios);
axios.get = (url, ...args) => String(url) === fake
    ? Promise.resolve({ data: { avatar: 'test-only' } }) : originalGet(url, ...args);
axios.post = async (url, data, ...args) => {
    const response = await originalPost(
        String(url) === fake ? process.env.KUMAOPS_VERIFY_SINK : url, data, ...args);
    if (process.env.KUMAOPS_REAL_TEST_WEBHOOK && String(url) === process.env.KUMAOPS_REAL_TEST_WEBHOOK) {
        // Record only the successful API response and payload, never the secret URL.
        await originalPost(process.env.KUMAOPS_VERIFY_SINK, {
            transport: 'real-discord', status: response.status, payload: data
        });
    }
    return response;
};
