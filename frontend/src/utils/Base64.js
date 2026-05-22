export const decode = param => decodeURIComponent(window.atob(param));
export const encode = param => window.btoa(encodeURIComponent(param));

export const decodeJson = param => JSON.parse(decode(param));
export const encodeJson = param => encode(JSON.stringify(param));

export const safeJsonParse = (value, fallback) => {
  try {
    return value ? decodeJson(value) : fallback;
  } catch {
    return fallback;
  }
};