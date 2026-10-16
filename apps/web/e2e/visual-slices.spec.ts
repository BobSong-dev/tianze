/**
 * 视觉自审辅助：把超高的全页截图裁成可查看的片段。
 * 仅用于人工复核，不参与产品构建。
 */
import { test } from "@playwright/test";
import fs from "node:fs";

const OUT = "test-results/visual";

test("crop tall screenshots into readable slices", async ({ page }) => {
  const targets = [
    { src: "07-knowledge-1440.png", slices: 2, name: "07-knowledge-1440" },
    { src: "10-report-1440.png", slices: 2, name: "10-report-1440" },
    { src: "23-knowledge-375.png", slices: 2, name: "23-knowledge-375" },
    { src: "06-temporal-1440.png", slices: 2, name: "06-temporal-1440" },
  ];

  for (const t of targets) {
    const p = `${OUT}/${t.src}`;
    if (!fs.existsSync(p)) continue;
    const b64 = fs.readFileSync(p).toString("base64");
    const dims = await page.evaluate(async (data) => {
      const img = new Image();
      await new Promise<void>((res, rej) => {
        img.onload = () => res();
        img.onerror = () => rej(new Error("load"));
        img.src = `data:image/png;base64,${data}`;
      });
      return { w: img.naturalWidth, h: img.naturalHeight };
    }, b64);

    const sliceH = Math.ceil(dims.h / t.slices);
    for (let i = 0; i < t.slices; i++) {
      const y = i * sliceH;
      const h = Math.min(sliceH, dims.h - y);
      if (h <= 0) continue;
      const out = await page.evaluate(async ({ data, y, h, w }) => {
        const img = new Image();
        await new Promise<void>((res, rej) => {
          img.onload = () => res();
          img.onerror = () => rej(new Error("load"));
          img.src = `data:image/png;base64,${data}`;
        });
        const c = document.createElement("canvas");
        c.width = w;
        c.height = h;
        const ctx = c.getContext("2d")!;
        ctx.drawImage(img, 0, y, w, h, 0, 0, w, h);
        return c.toDataURL("image/png").split(",")[1];
      }, { data: b64, y, h, w: dims.w });
      fs.writeFileSync(`${OUT}/${t.name}-part${i + 1}.png`, Buffer.from(out, "base64"));
    }
  }
});
