/**
 * draftExport.js
 * 레이어: Utils (srTemplates/core)
 * 역할: 보고서 초안 화면을 PDF 또는 PPT(이미지형/편집형)로 내보내는 비동기 내보내기 유틸
 *
 * exports:
 *   exportPdf — 서브이슈 페이지를 A4 가로 PDF로 저장 (목차·페이지 내부 링크 포함)
 *   exportPptNative — DOM 요소를 직접 파싱해 텍스트·표·도형 기반 편집형 PPTX로 저장
 *   exportPptImg — 각 페이지를 canvas 이미지로 캡처한 이미지형 PPTX로 저장
 */
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import pptxgen from "pptxgenjs";
import { subIssues } from "../registry";

async function _waitFrames() {
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  await new Promise((r) => setTimeout(r, 120));
}

function _renderEl(el, bg = "#ffffff") {
  return html2canvas(el, {
    scale: 2, useCORS: true, allowTaint: true, backgroundColor: bg,
    width: el.offsetWidth, height: el.offsetHeight, windowWidth: el.offsetWidth,
  });
}

export async function exportPdf(setPdfMode) {
  setPdfMode(true);
  await _waitFrames();
  try {
    const root = document.getElementById("pdf-render-root");
    if (!root) return;

    const pdf = new jsPDF("l", "mm", "a4");
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    let pdfFirstPage = true;

    const pendingTocLinks = [];
    const pendingSubnavLinks = [];
    const globalPdfPageOf = {};

    const tocEl = root.querySelector(`#pdf-toc-combined`);
    if (tocEl) {
      if (!pdfFirstPage) pdf.addPage();
      pdfFirstPage = false;
      const tocPdfPage = pdf.getNumberOfPages();
      const tocCanvas = await _renderEl(tocEl);
      const tocImgH = Math.min((tocCanvas.height * pageW) / tocCanvas.width, pageH);
      pdf.addImage(tocCanvas.toDataURL("image/png"), "PNG", 0, 0, pageW, tocImgH);
      const tocRect = tocEl.getBoundingClientRect();
      const tocMmPerPx = pageW / tocRect.width;
      for (const si of subIssues) {
        si.pages.forEach((p) => {
          const item = root.querySelector(`#pdf-tocitem-${si.id}-${p.key}`);
          if (!item) return;
          const r = item.getBoundingClientRect();
          pendingTocLinks.push({
            tocPdfPage, key: p.key,
            x: (r.left - tocRect.left) * tocMmPerPx,
            y: (r.top - tocRect.top) * tocMmPerPx,
            w: r.width * tocMmPerPx,
            h: r.height * tocMmPerPx,
          });
        });
      }
    }

    for (const si of subIssues) {
      for (const page of si.pages) {
        const sec = root.querySelector(`#pdf-sec-${si.id}-${page.key} .sr-page`);
        if (!sec) continue;
        const canvas = await _renderEl(sec);
        if (!pdfFirstPage) pdf.addPage();
        pdfFirstPage = false;
        const thisPdfPage = pdf.getNumberOfPages();
        globalPdfPageOf[page.key] = thisPdfPage;

        const imgH = (canvas.height * pageW) / canvas.width;
        pdf.addImage(canvas.toDataURL("image/png"), "PNG", 0, 0, pageW, imgH);

        const secRect = sec.getBoundingClientRect();
        const mmPerPx = pageW / secRect.width;
        sec.querySelectorAll(".sr-subnav span:not(.dot)").forEach((tab, ti) => {
          if (ti >= si.pages.length) return;
          const r = tab.getBoundingClientRect();
          pendingSubnavLinks.push({
            onPdfPage: thisPdfPage,
            x: (r.left - secRect.left) * mmPerPx,
            y: (r.top - secRect.top) * mmPerPx,
            w: r.width * mmPerPx,
            h: r.height * mmPerPx,
            targetKey: si.pages[ti].key,
          });
        });
      }
    }

    pendingTocLinks.forEach((l) => {
      const t = globalPdfPageOf[l.key];
      if (!t) return;
      pdf.setPage(l.tocPdfPage);
      pdf.link(l.x, l.y, l.w, Math.max(l.h, 4), { pageNumber: t });
    });
    pendingSubnavLinks.forEach((l) => {
      const t = globalPdfPageOf[l.targetKey];
      if (!t) return;
      pdf.setPage(l.onPdfPage);
      pdf.link(l.x, l.y, l.w, Math.max(l.h, 4), { pageNumber: t });
    });

    pdf.save("esg-sustainability-report.pdf");
  } finally {
    setPdfMode(false);
  }
}

export async function exportPptNative(setPdfMode) {
  setPdfMode(true);
  await _waitFrames();
  try {
    const root = document.getElementById("pdf-render-root");
    if (!root) return;

    const SLIDE_W = 11.69, SLIDE_H = 8.27;
    const FONT = "Malgun Gothic";

    const toHex = (rgb) => {
      const m = (rgb || "").match(/\d+(\.\d+)?/g);
      if (!m || m.length < 3) return null;
      const [r, g, b] = m.map(Number);
      return [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("").toUpperCase();
    };

    const pptx = new pptxgen();
    pptx.defineLayout({ name: "A4L", width: SLIDE_W, height: SLIDE_H });
    pptx.layout = "A4L";
    let slideNo = 0;

    const makeCtx = (sec) => {
      const pageRect = sec.getBoundingClientRect();
      const k = SLIDE_W / pageRect.width;
      const pos = (el) => { const r = el.getBoundingClientRect(); return { x: (r.left - pageRect.left) * k, y: (r.top - pageRect.top) * k, w: r.width * k, h: r.height * k }; };
      const fpt = (el) => Math.max(6, parseFloat(getComputedStyle(el).fontSize) * k * 72);
      return { k, pos, fpt };
    };

    const addTextEl = (slide, el, ctx, extra = {}) => {
      const txt = (el.innerText || "").trim();
      if (!txt) return;
      const cs = getComputedStyle(el);
      const p = ctx.pos(el);
      slide.addText(txt, {
        x: p.x, y: p.y, w: p.w, h: Math.max(p.h, 0.18),
        fontSize: ctx.fpt(el), fontFace: FONT,
        bold: parseInt(cs.fontWeight, 10) >= 600,
        color: toHex(cs.color) || "16241F",
        align: cs.textAlign === "right" ? "right" : cs.textAlign === "center" ? "center" : "left",
        valign: "top", margin: 1, ...extra,
      });
    };

    const buildSlide = async (sec) => {
      const ctx = makeCtx(sec);
      const slide = pptx.addSlide();

      const topband = sec.querySelector(".sr-topband");
      if (topband) { const p = ctx.pos(topband); slide.addShape(pptx.ShapeType.rect, { x: p.x, y: p.y, w: p.w, h: Math.max(p.h, 0.04), fill: { color: toHex(getComputedStyle(topband).backgroundColor) || "16241F" }, line: { width: 0 } }); }

      const subnav = sec.querySelector(".sr-subnav");
      if (subnav) addTextEl(slide, subnav, ctx, { color: "6b8378" });

      ["sr-eyebrow", "sr-title", "sr-title-en"].forEach((cls) => { const el = sec.querySelector("." + cls); if (el) addTextEl(slide, el, ctx); });

      const prose = sec.querySelector(".sr-prose");
      if (prose) addTextEl(slide, prose, ctx);

      sec.querySelectorAll(".sr-kpi").forEach((card) => {
        const cs = getComputedStyle(card); const p = ctx.pos(card);
        slide.addShape(pptx.ShapeType.roundRect, { x: p.x, y: p.y, w: p.w, h: p.h, rectRadius: 0.05, fill: { color: toHex(cs.backgroundColor) || "F4F8F6" }, line: { color: toHex(cs.borderTopColor) || "D7E2DC", width: 0.5 } });
        ["kl", "kv", "kd"].forEach((c) => { const el = card.querySelector("." + c); if (el) addTextEl(slide, el, ctx); });
      });

      sec.querySelectorAll(".sr-tcap").forEach((cap) => addTextEl(slide, cap, ctx, { bold: true }));
      sec.querySelectorAll("table.sr-tbl").forEach((tbl) => {
        const p = ctx.pos(tbl);
        const rows = [];
        tbl.querySelectorAll("tr").forEach((tr) => {
          const cells = [];
          tr.querySelectorAll("th,td").forEach((td) => {
            const cs = getComputedStyle(td);
            cells.push({
              text: (td.innerText || "").trim(), options: {
                bold: td.tagName === "TH" || parseInt(cs.fontWeight, 10) >= 600,
                color: toHex(cs.color) || "16241F",
                fill: { color: td.tagName === "TH" ? "EAF3EE" : "FFFFFF" },
                align: cs.textAlign === "right" ? "right" : cs.textAlign === "center" ? "center" : "left",
                fontSize: Math.max(7, ctx.fpt(td)), valign: "middle",
              }
            });
          });
          if (cells.length) rows.push(cells);
        });
        const headCells = tbl.querySelectorAll("tr:first-child th, tr:first-child td");
        const colW = Array.from(headCells).map((c) => c.getBoundingClientRect().width * ctx.k);
        if (rows.length) slide.addTable(rows, { x: p.x, y: p.y, w: p.w, colW: colW.length ? colW : undefined, border: { type: "solid", pt: 0.5, color: "D7E2DC" }, fontFace: FONT, autoPage: false, valign: "middle" });
      });

      for (const sel of [".sr-road", ".sr-gauge"]) {
        const el = sec.querySelector(sel);
        if (el) { const p = ctx.pos(el); const cv = await _renderEl(el, null); slide.addImage({ data: cv.toDataURL("image/png"), x: p.x, y: p.y, w: p.w, h: p.h }); }
      }

      sec.querySelectorAll(".sr-note-card").forEach((card) => {
        const cs = getComputedStyle(card); const p = ctx.pos(card);
        slide.addShape(pptx.ShapeType.roundRect, { x: p.x, y: p.y, w: p.w, h: p.h, rectRadius: 0.04, fill: { color: toHex(cs.backgroundColor) || "F4F8F6" }, line: { color: "D7E2DC", width: 0.5 } });
        ["l", "b", "s"].forEach((c) => { const el = card.querySelector("." + c); if (el) addTextEl(slide, el, ctx); });
      });

      const measures = sec.querySelector(".sr-measures");
      if (measures) {
        const cs = getComputedStyle(measures); const p = ctx.pos(measures);
        slide.addShape(pptx.ShapeType.rect, { x: p.x, y: p.y, w: p.w, h: p.h, fill: { color: toHex(cs.backgroundColor) || "F4F8F6" }, line: { width: 0 } });
        ["ml", "mv"].forEach((c) => { const el = measures.querySelector("." + c); if (el) addTextEl(slide, el, ctx); });
      }

      const foot = sec.querySelector(".sr-foot");
      if (foot && (foot.innerText || "").trim()) addTextEl(slide, foot, ctx, { color: "8aa399" });

      return slide;
    };

    const tocSlide = pptx.addSlide(); slideNo++;
    tocSlide.addText("ESG 지속가능경영 보고서", { x: 0.6, y: 0.5, w: SLIDE_W - 1.2, h: 0.6, fontSize: 24, bold: true, color: "1B5E44", fontFace: FONT });
    tocSlide.addText("목차", { x: 0.6, y: 1.2, w: 3, h: 0.4, fontSize: 13, color: "6B8378", fontFace: FONT });

    const tocItems = [];
    for (const si of subIssues) {
      for (const page of si.pages) {
        const sec = root.querySelector(`#pdf-sec-${si.id}-${page.key} .sr-page`);
        if (!sec) continue;
        await buildSlide(sec);
        slideNo++;
        tocItems.push({ label: `[${si.label}] ${page.tabLabel || page.key}`, slide: slideNo });
      }
    }
    tocItems.forEach((it, i) => {
      tocSlide.addText(`${i + 1}. ${it.label}`, { x: 0.8, y: 1.7 + i * 0.5, w: SLIDE_W - 1.6, h: 0.42, fontSize: 15, color: "16241F", fontFace: FONT, hyperlink: { slide: it.slide } });
    });

    await pptx.writeFile({ fileName: "esg-sustainability-report-편집형.pptx" });
  } finally {
    setPdfMode(false);
  }
}

export async function exportPptImg(setPdfMode) {
  setPdfMode(true);
  await _waitFrames();
  try {
    const root = document.getElementById("pdf-render-root");
    if (!root) return;

    const SLIDE_W = 11.69, SLIDE_H = 8.27;

    const pptx = new pptxgen();
    pptx.defineLayout({ name: "A4L", width: SLIDE_W, height: SLIDE_H });
    pptx.layout = "A4L";

    const slideOf = {};
    const createdSlides = {};
    let slideNo = 0;
    const tocAreas = [];
    const subnavAreas = [];

    const tocEl = root.querySelector(`#pdf-toc-combined`);
    if (tocEl) {
      const tocCanvas = await _renderEl(tocEl);
      const tocSlide = pptx.addSlide(); slideNo++; createdSlides[slideNo] = tocSlide;
      const tocSlideNo = slideNo;
      tocSlide.addImage({ data: tocCanvas.toDataURL("image/png"), x: 0, y: 0, w: SLIDE_W, h: SLIDE_H });
      const tocRect = tocEl.getBoundingClientRect();
      const inPerPx = SLIDE_W / tocRect.width;
      for (const si of subIssues) {
        si.pages.forEach((p) => {
          const item = root.querySelector(`#pdf-tocitem-${si.id}-${p.key}`);
          if (!item) return;
          const r = item.getBoundingClientRect();
          tocAreas.push({
            tocSlideNo, key: p.key,
            x: (r.left - tocRect.left) * inPerPx,
            y: (r.top - tocRect.top) * inPerPx,
            w: r.width * inPerPx,
            h: r.height * inPerPx,
          });
        });
      }
    }

    for (const si of subIssues) {
      for (const page of si.pages) {
        const sec = root.querySelector(`#pdf-sec-${si.id}-${page.key} .sr-page`);
        if (!sec) continue;
        const canvas = await _renderEl(sec);
        const slide = pptx.addSlide(); slideNo++; createdSlides[slideNo] = slide;
        slideOf[page.key] = slideNo;
        slide.addImage({ data: canvas.toDataURL("image/png"), x: 0, y: 0, w: SLIDE_W, h: SLIDE_H });

        const secRect = sec.getBoundingClientRect();
        const inPerPx = SLIDE_W / secRect.width;
        sec.querySelectorAll(".sr-subnav span:not(.dot)").forEach((tab, ti) => {
          if (ti >= si.pages.length) return;
          const r = tab.getBoundingClientRect();
          subnavAreas.push({
            onSlide: slideNo,
            targetKey: si.pages[ti].key,
            x: (r.left - secRect.left) * inPerPx,
            y: (r.top - secRect.top) * inPerPx,
            w: r.width * inPerPx,
            h: r.height * inPerPx,
          });
        });
      }
    }

    const addLink = (slide, a, t) =>
      slide.addShape(pptx.ShapeType.rect, {
        x: a.x, y: a.y, w: a.w, h: Math.max(a.h, 0.12),
        fill: { color: "FFFFFF", transparency: 100 },
        line: { color: "FFFFFF", transparency: 100, width: 0 },
        hyperlink: { slide: t },
      });
    tocAreas.forEach((a) => {
      const t = slideOf[a.key];
      const s = createdSlides[a.tocSlideNo];
      if (t && s) addLink(s, a, t);
    });
    subnavAreas.forEach((a) => {
      const t = slideOf[a.targetKey];
      const s = createdSlides[a.onSlide];
      if (t && s) addLink(s, a, t);
    });

    await pptx.writeFile({ fileName: "esg-sustainability-report.pptx" });
  } finally {
    setPdfMode(false);
  }
}
