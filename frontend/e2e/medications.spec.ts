import { test, expect } from './fixtures';
const plan={id:'p1',patient_id:'demo',doctor_id:'doc',medicine:'Thuốc mô phỏng',prescribed_dose:'Theo đơn mô phỏng',prescription_reference:'TEST-001',times:['08:00'],start_date:'2026-10-01',end_date:'2026-10-01',status:'approved',schedule:[{due_at:'2026-10-01T08:00:00+07:00',status:'overdue'}],adherence:{due:1,taken:0,rate:0}};
test('patient records one approved dose and sees updated adherence',async({page})=>{
 await page.route('**/v1/auth/me',r=>r.fulfill({json:{id:'demo',username:'demo',role:'user'}}));
 let taken=false;
 await page.route('**/v1/medications/patients/demo',r=>r.fulfill({json:{plans:[{...plan,schedule:[{...plan.schedule[0],status:taken?'taken':'overdue'}],adherence:{due:1,taken:taken?1:0,rate:taken?1:0}}]}}));
 await page.route('**/v1/medications/plans/p1/doses',async r=>{expect(r.request().postDataJSON().status).toBe('taken');taken=true;await r.fulfill({json:{status:'taken'}});});
 await page.goto('/medications');
 await page.getByRole('button',{name:'Đã dùng',exact:true}).click();
 await expect(page.getByText(/Đã xác nhận dùng 1\/1/)).toBeVisible();
 await expect(page.getByRole('button',{name:'Đã dùng',exact:true})).toHaveCount(0);
});
test('doctor reviews a draft before approving',async({page})=>{
 await page.route('**/v1/auth/me',r=>r.fulfill({json:{id:'doc',username:'doctor',role:'doctor'}}));
 let approved=false;
 await page.route('**/v1/medications/patients/demo',r=>r.fulfill({json:{plans:[{...plan,status:approved?'approved':'draft',schedule:[]}]}}));
 await page.route('**/v1/medications/plans/p1/approve',async r=>{approved=true;await r.fulfill({json:{status:'approved'}});});
 await page.goto('/medications');
 await page.getByLabel('Mã bệnh nhân').fill('demo');
 await page.getByRole('button',{name:'Xem lịch bệnh nhân'}).click();
 await expect(page.getByText('Bản nháp — chưa áp dụng')).toBeVisible();
 await page.getByRole('button',{name:'Duyệt lịch theo đơn'}).click();
 await expect(page.getByText('Bác sĩ đã duyệt',{exact:true})).toBeVisible();
});