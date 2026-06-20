/**
 * Base64.js
 * 레이어: Utils
 * 역할: Base64 인코딩/디코딩 유틸 — localStorage 직렬화·역직렬화에 사용.
 *
 * exports:
 *   decode        — Base64 문자열을 UTF-8 문자열로 디코딩
 *   encode        — UTF-8 문자열을 Base64로 인코딩
 *   decodeJson    — Base64 문자열을 JSON 파싱해 객체로 반환
 *   encodeJson    — 객체를 JSON 직렬화 후 Base64로 인코딩
 *   safeJsonParse — 디코딩 실패 시 fallback 값을 반환하는 안전한 파싱
 */
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