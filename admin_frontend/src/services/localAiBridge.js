/**
 * Bridge server AI lokal (LM Studio/Ollama) dari BROWSER user.
 *
 * Backend (Docker/VPS) tidak dapat menjangkau localhost di laptop user — hanya
 * browser-lah yang bisa. Modul ini menjembatani: mengambil prompt siap pakai
 * dari backend, memanggil server AI di laptop user, lalu menyerahkan jawaban
 * mentah ke backend untuk divalidasi & disimpan.
 *
 * Timeout & retry mengikuti paritas backend: 120s per panggilan, 1 retry pada
 * kegagalan jaringan (delay 2 detik, model cold-load/server sibuk).
 */

const DEFAULT_TIMEOUT_MS = 120000;
const LIST_MODELS_TIMEOUT_MS = 15000;
const RETRY_DELAY_MS = 2000;

export function describeBridgeNetworkError(provider, baseUrl) {
  const origin = window.location.origin;
  if (provider === 'ollama') {
    return `Tidak dapat menghubungi server AI di ${baseUrl} dari browser. `
      + `Pastikan Ollama berjalan di laptop Anda DAN mengizinkan origin ${origin} — `
      + `mis. jalankan: OLLAMA_ORIGINS="${origin},http://localhost:*" ollama serve`;
  }
  if (provider === 'lmstudio') {
    return `Tidak dapat menghubungi server AI di ${baseUrl} dari browser. `
      + `Pastikan LM Studio Server berjalan (tab Developer → Start Server) DAN opsi `
      + `"Enable CORS" aktif agar origin ${origin} diizinkan.`;
  }
  return `Tidak dapat menghubungi server AI di ${baseUrl} dari browser. `
    + `Pastikan server berjalan dan mengizinkan origin ${origin}.`;
}

export async function fetchWithTimeout(url, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

const isNetworkFailure = (err) => err instanceof TypeError || err?.name === 'AbortError';

/** Satu panggilan /chat/completions ke laptop user; balikan teks isi pesan. */
export async function chatCompletionViaBridge(settings, prompt) {
  const base = String(settings?.base_url || '').replace(/\/+$/, '');
  const timeoutMs = (Number(settings?.timeout) || DEFAULT_TIMEOUT_MS / 1000) * 1000;
  const body = JSON.stringify({
    model: prompt.model,
    messages: prompt.messages,
    temperature: prompt.temperature ?? 0.1,
    max_tokens: prompt.max_tokens ?? 800,
    stream: false,
  });
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetchWithTimeout(`${base}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body,
      }, timeoutMs);
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 500);
        throw new Error(`Server AI menjawab HTTP ${response.status}: ${detail}`);
      }
      const data = await response.json();
      const message = data?.choices?.[0]?.message || {};
      // Model reasoning kadang menghabiskan token di field terpisah — paritas backend.
      const content = String(message.content || '').trim()
        || String(message.reasoning || '').trim();
      if (!content) throw new Error('Server AI mengembalikan isi pesan kosong.');
      return content;
    } catch (err) {
      if (attempt === 0 && isNetworkFailure(err)) {
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
        continue;
      }
      if (isNetworkFailure(err)) {
        throw new Error(describeBridgeNetworkError(settings?.provider, base));
      }
      throw err;
    }
  }
  throw new Error('Server AI tidak menjawab tepat waktu (timeout).');
}

/** Daftar model dari server AI lokal, langsung dari browser (timeout 15s). */
export async function listLocalModels(settings) {
  const base = String(settings?.base_url || '').replace(/\/+$/, '');
  let response;
  try {
    response = await fetchWithTimeout(
      `${base}/models`,
      { headers: { Accept: 'application/json' } },
      LIST_MODELS_TIMEOUT_MS,
    );
  } catch (err) {
    throw new Error(describeBridgeNetworkError(settings?.provider, base));
  }
  if (!response.ok) {
    throw new Error(`Server AI menjawab HTTP ${response.status}.`);
  }
  const data = await response.json();
  const items = Array.isArray(data) ? data : (data.data || []);
  return items
    .map((item) => (typeof item === 'string' ? item : String(item?.id || '')))
    .filter(Boolean);
}

/**
 * Alur suggest lengkap via bridge: prepare → panggil LLM lokal per prompt
 * (sekuensial, paritas loop server) → submit jawaban mentah.
 * Balikan {results} gabungan — shape item identik endpoint lama.
 */
export async function runBridgeSuggest(aiApi, ids, settings) {
  const { data: prep } = await aiApi.prepareSuggest(ids);
  const items = [];
  for (const prompt of prep.pending || []) {
    try {
      const raw = await chatCompletionViaBridge(settings, prompt);
      items.push({ id: prompt.id, raw });
    } catch (err) {
      items.push({ id: prompt.id, error: String(err?.message || err) });
    }
  }
  let llmResults = [];
  if (items.length > 0) {
    const { data } = await aiApi.submitSuggest(items);
    llmResults = data.results || [];
  }
  return { results: [...(prep.results || []), ...llmResults] };
}
