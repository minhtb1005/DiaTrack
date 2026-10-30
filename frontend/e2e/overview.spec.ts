import { test, expect } from './fixtures';
test('pitch explains the product without internal infrastructure',async({page})=>{
 await page.goto('/');
 await expect(page.getByRole('heading',{level:1})).toContainText('Chăm sóc đường huyết');
 await expect(page.getByRole('link',{name:/Bắt đầu cùng DiaTrack/})).toHaveAttribute('href','/register');
 await expect(page.locator('main')).not.toContainText(/localhost|vnstoc?k|Chroma|Corpus|RAG|FastAPI|KPI|API Status|BHYT|PDFs/i);
 await page.getByText('Lịch thuốc lấy từ đâu?',{exact:true}).click();
 await expect(page.getByText(/Bác sĩ nhập lịch theo đơn/)).toBeVisible();
});
test('mobile navigation exposes patient tasks without horizontal overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.route('**/v1/auth/me',r=>r.fulfill({json:{id:'demo',username:'demo',role:'user'}}));
 await page.goto('/');
 await page.getByRole('button',{name:'Mở menu'}).click();
 const nav=page.getByRole('navigation',{name:'Điều hướng di động'});
 await expect(nav.getByRole('link',{name:'Sổ đường huyết'})).toBeVisible();
 await expect(nav.getByRole('link',{name:'Lịch thuốc'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
test('pitch is usable without backend availability',async({page})=>{
 await page.route('**/v1/**',r=>r.abort());
 await page.goto('/');
 await expect(page.getByRole('heading',{level:1})).toBeVisible();
 await expect(page.locator('main')).not.toContainText('undefined');
});

test('doctor dashboard separates critical from watch and links approval queue', async ({ page }) => {
 await page.route('**/v1/auth/me', r => r.fulfill({json:{id:'doctor-1',username:'doctor',role:'doctor',is_active:true,is_verified:true}}));
 await page.route('**/v1/doctor/patients**', r => r.fulfill({json:{patients:[
  {user_id:'patient-1',username:'Bệnh nhân A',last_value:300,last_classification:'critical',level:'critical',anomaly_count:1},
  {user_id:'patient-2',username:'Bệnh nhân B',last_value:280,last_classification:'high',level:'watch',anomaly_count:1},
 ],total:2,limit:100,offset:0}}));
 await page.goto('/expert/patients');
 await expect(page.getByTestId('queue-row')).toHaveCount(2);
 await expect(page.getByText('Bệnh nhân A')).toBeVisible();
 await expect(page.getByText('Bệnh nhân B')).toBeVisible();
 await expect(page.getByRole('link',{name:'Duyệt nội dung chờ bác sĩ'})).toHaveAttribute('href','/expert/queue');
});
