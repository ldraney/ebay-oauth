const express = require('express');
const https = require('https');

const app = express();
const PORT = process.env.PORT || 3000;

const CLIENT_ID = process.env.EBAY_CLIENT_ID;
const CLIENT_SECRET = process.env.EBAY_CLIENT_SECRET;
const RUNAME = process.env.EBAY_RUNAME;
const DEFAULT_LOCALHOST_PORT = 8881;

const EBAY_CONFIG = {
  sandbox: {
    consentUrl: 'https://auth.sandbox.ebay.com/oauth2/authorize',
    tokenHost: 'api.sandbox.ebay.com',
    tokenPath: '/identity/v1/oauth2/token',
  },
  production: {
    consentUrl: 'https://auth.ebay.com/oauth2/authorize',
    tokenHost: 'api.ebay.com',
    tokenPath: '/identity/v1/oauth2/token',
  },
};

const SCOPES = [
  'https://api.ebay.com/oauth/api_scope',
  'https://api.ebay.com/oauth/api_scope/sell.inventory',
  'https://api.ebay.com/oauth/api_scope/sell.inventory.readonly',
  'https://api.ebay.com/oauth/api_scope/sell.account',
  'https://api.ebay.com/oauth/api_scope/sell.account.readonly',
  'https://api.ebay.com/oauth/api_scope/sell.fulfillment',
  'https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly',
  'https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly',
].join(' ');

function encodeState(port, nonce, environment) {
  const data = JSON.stringify({ port, nonce, environment });
  return Buffer.from(data).toString('base64url');
}

function decodeState(state) {
  try {
    const data = Buffer.from(state, 'base64url').toString('utf8');
    return JSON.parse(data);
  } catch {
    return { port: DEFAULT_LOCALHOST_PORT, nonce: null, environment: 'sandbox' };
  }
}

// Step 1: Redirect user to eBay OAuth consent
app.get('/auth/ebay', (req, res) => {
  if (!CLIENT_ID || !RUNAME) {
    return res.status(500).json({ error: 'EBAY_CLIENT_ID or EBAY_RUNAME not configured' });
  }

  const port = parseInt(req.query.port, 10) || DEFAULT_LOCALHOST_PORT;
  const nonce = req.query.nonce || null;
  const environment = req.query.environment || 'sandbox';

  const config = EBAY_CONFIG[environment] || EBAY_CONFIG.sandbox;
  const state = encodeState(port, nonce, environment);

  const authUrl = new URL(config.consentUrl);
  authUrl.searchParams.set('client_id', CLIENT_ID);
  authUrl.searchParams.set('response_type', 'code');
  authUrl.searchParams.set('redirect_uri', RUNAME);
  authUrl.searchParams.set('scope', SCOPES);
  authUrl.searchParams.set('state', state);

  res.redirect(authUrl.toString());
});

// Step 2: Handle callback from eBay, exchange code for tokens
app.get('/auth/callback', async (req, res) => {
  const { code, error, error_description, state } = req.query;

  const { port, nonce, environment } = decodeState(state);

  if (error) {
    return redirectToLocalhost(res, port, nonce, { error, error_description });
  }

  if (!code) {
    return redirectToLocalhost(res, port, nonce, { error: 'missing_code' });
  }

  try {
    const tokenData = await exchangeCodeForToken(code, environment);
    redirectToLocalhost(res, port, nonce, {
      access_token: tokenData.access_token,
      refresh_token: tokenData.refresh_token,
      expires_in: tokenData.expires_in,
      refresh_token_expires_in: tokenData.refresh_token_expires_in,
    });
  } catch (err) {
    console.error('OAuth error:', err);
    redirectToLocalhost(res, port, nonce, { error: 'token_exchange_failed', error_description: err.message });
  }
});

function redirectToLocalhost(res, port, nonce, params) {
  const url = new URL(`http://localhost:${port}/callback`);
  if (nonce) {
    url.searchParams.set('nonce', nonce);
  }
  Object.entries(params).forEach(([key, value]) => {
    if (value != null) url.searchParams.set(key, String(value));
  });
  res.redirect(url.toString());
}

function exchangeCodeForToken(code, environment) {
  const config = EBAY_CONFIG[environment] || EBAY_CONFIG.sandbox;

  // eBay uses Basic auth: base64(client_id:client_secret)
  const credentials = Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString('base64');

  const postData = new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    redirect_uri: RUNAME,
  }).toString();

  return new Promise((resolve, reject) => {
    const options = {
      hostname: config.tokenHost,
      path: config.tokenPath,
      method: 'POST',
      family: 4,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': `Basic ${credentials}`,
        'Content-Length': Buffer.byteLength(postData),
      },
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.error) {
            reject(new Error(parsed.error_description || parsed.error));
          } else {
            resolve(parsed);
          }
        } catch (e) {
          reject(new Error('Failed to parse token response'));
        }
      });
    });

    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, () => {
  console.log(`eBay OAuth relay running on port ${PORT}`);
});
