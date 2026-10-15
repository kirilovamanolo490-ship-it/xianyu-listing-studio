if (process.env.XIANYU_ENABLE_LEGACY_WORKFLOWS !== '1') {
  throw new Error('Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.');
}

const {chromium} = require(process.env.XIANYU_LEGACY_PLAYWRIGHT_PATH || 'playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const base = process.env.XIANYU_LEGACY_SOURCE_ROOT || path.resolve(process.cwd(), 'legacy-preview');
const report = {checked_at:new Date().toISOString(), views:[], errors:[]};
const url = process.env.XIANYU_LEGACY_PREVIEW_URL || 'http://127.0.0.1:8768/完整商品图_v4/预览.html';
(async()=>{
  const browser = await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  try {
    for (const viewport of [{width:1440,height:1000},{width:390,height:844}]) {
      const page = await browser.newPage({viewport});
      page.on('pageerror',e=>report.errors.push(String(e)));
      page.on('response',r=>{if(r.status()>=400)report.errors.push(r.status()+' '+r.url())});
      await page.goto(url,{waitUntil:'networkidle'});
      for(const code of ['ZG','CS']) {
        await page.locator('[data-code="'+code+'"]').click();
        await page.waitForFunction(()=>document.querySelectorAll('.card').length===9);
        await page.locator('.card img').evaluateAll(ims=>ims.forEach(im=>im.loading='eager'));
        await page.waitForFunction(()=>[...document.querySelectorAll('.card img')].every(im=>im.complete&&im.naturalWidth===1800&&im.naturalHeight===2400));
        const value = await page.evaluate(async()=>{
          const links=[...document.querySelectorAll('a[download]')].map(a=>a.href);
          const downloads=[];
          for(const href of links){const r=await fetch(href,{method:'HEAD'});downloads.push({url:href,status:r.status,bytes:Number(r.headers.get('content-length'))})}
          const originalPages=[...document.querySelectorAll('.pages img')].map(im=>im.src);
          const sourceChecks=[]; for(const src of originalPages){sourceChecks.push({status:(await fetch(src,{method:'HEAD'})).status})}
          return {count:document.querySelectorAll('.card').length,downloads,source_pages:originalPages.length,source_pages_ok:sourceChecks.every(x=>x.status===200),initially_collapsed:[...document.querySelectorAll('.pages')].every(el=>getComputedStyle(el).display==='none'),viewport_width:innerWidth,document_width:document.documentElement.scrollWidth,share:[...document.querySelectorAll('a')].find(a=>a.hostname==='pan.quark.cn')?.href};
        });
        assert.equal(value.count,9); assert(value.downloads.every(x=>x.status===200&&x.bytes>100));
        assert(value.source_pages_ok);assert(value.initially_collapsed);assert(value.document_width<=value.viewport_width);
        assert.equal(value.source_pages,code==='ZG'?48:42);
        const expectedShareId = code === 'CS' ? process.env.XIANYU_LEGACY_SHARE_ID_CS : process.env.XIANYU_LEGACY_SHARE_ID_ZG;
        if (!expectedShareId) throw new Error('Set the legacy share ID environment variable locally after confirming authorization.');
        assert(value.share.includes(expectedShareId));
        await page.locator('.card img').first().click();
        assert(await page.locator('dialog').isVisible());
        await page.locator('dialog button').click();
        await page.locator('[data-deck="0"]').click();
        assert(await page.locator('#deck-0').isVisible());
        await page.locator('[data-deck="0"]').click();
        assert(!(await page.locator('#deck-0').isVisible()));
        await page.evaluate(()=>window.scrollTo(0,0));
        await page.screenshot({path:path.join(base,'检查',code+'_'+viewport.width+'预览.png')});
        report.views.push({code,viewport,...value});
      }
      await page.close();
    }
    assert.equal(report.errors.length,0);
    report.status='passed';
  } catch(e) {report.status='failed';report.failure=String(e);process.exitCode=1}
  finally {await browser.close();fs.writeFileSync(path.join(base,'检查/预览核查.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,views:report.views.length,errors:report.errors,failure:report.failure}))}
})();
