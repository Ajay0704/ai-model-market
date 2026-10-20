// Publish (or update) the PBIR report through the Fabric REST API, from a signed-in app.powerbi.com tab.
// Run in the page console. The page's own session token is used inside the page and never printed.
// The base theme part is copied from any existing report (getDefinition), per Ajay0704/ecommerce-powerbi build notes.
async function publishReport({ws, bundleUrl, baseParts, reportId = null, name = 'AI Model Market'}) {
  const H = {Authorization: 'Bearer ' + window.powerBIAccessToken, 'Content-Type': 'application/json'};
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const files = await (await fetch(bundleUrl, {cache: 'no-store'})).json();
  const b64 = s => btoa(unescape(encodeURIComponent(s)));
  const parts = Object.entries(files).map(([path, text]) => ({path, payload: b64(text), payloadType: 'InlineBase64'})).concat(baseParts);
  const url = reportId ? `https://api.fabric.microsoft.com/v1/workspaces/${ws}/reports/${reportId}/updateDefinition`
                       : `https://api.fabric.microsoft.com/v1/workspaces/${ws}/reports`;
  const body = reportId ? {definition: {parts}} : {displayName: name, definition: {parts}};
  let r = await fetch(url, {method: 'POST', headers: H, body: JSON.stringify(body)});
  if (r.status === 202) {
    const loc = r.headers.get('Location');
    for (let i = 0; i < 60; i++) { await sleep(2000); const j = await (await fetch(loc, {headers: H})).json();
      if (j.status === 'Succeeded') { const res = await fetch(loc + '/result', {headers: H}); return {ok: true, result: res.ok ? await res.json() : null}; }
      if (j.status === 'Failed') return {ok: false, error: j.error}; }
    return {ok: false, error: 'timeout'};
  }
  return {ok: r.ok, status: r.status, body: await r.text()};
}
