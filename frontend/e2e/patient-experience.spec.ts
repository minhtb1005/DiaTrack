import {test,expect} from './fixtures';
const user={id:'patient',username:'patient',role:'user'};
test('login has visible labels, password reveal and navigates to the daily task',async({page})=>{
 await page.route('**/v1/auth/me',r=>r.fulfill({status:401,json:{}}));
 await page.route('**/v1/auth/login',r=>r.fulfill({json:{user}}));
 await page.goto('/login');
 await page.getByLabel('Tên đăng nhập',{exact:true}).fill('patient');
 await page.getByLabel('Mật khẩu',{exact:true}).fill('test-only');
 await page.getByLabel('Hiện mật khẩu').check();
 await expect(page.getByLabel('Mật khẩu',{exact:true})).toHaveAttribute('type','text');
 await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();
 await expect(page).toHaveURL(/\/tracker$/);
});
test('login error stays readable and preserves user input',async({page})=>{
 await page.route('**/v1/auth/me',r=>r.fulfill({status:401,json:{}}));
 await page.route('**/v1/auth/login',r=>r.fulfill({status:401,json:{detail:'Unauthorized'}}));
 await page.goto('/login');
 await page.getByLabel('Tên đăng nhập',{exact:true}).fill('patient');
 await page.getByLabel('Mật khẩu',{exact:true}).fill('test-only');
 await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();
 await expect(page.locator('main').getByRole('alert')).toContainText('Chưa đăng nhập được');
 await expect(page.getByLabel('Tên đăng nhập',{exact:true})).toHaveValue('patient');
});
test('patient Q&A hides unapproved answer and offers review history',async({page})=>{
 await page.route('**/v1/auth/me',r=>r.fulfill({json:user}));
 await page.route('**/v1/query',r=>r.fulfill({json:{status:'pending_review',answer:'SECRET_UNAPPROVED_DRAFT'}}));
 await page.goto('/api-playground');
 await page.getByRole('button',{name:'Tôi nên chuẩn bị gì cho lần tái khám?'}).click();
 await expect(page.getByLabel('Câu hỏi của bạn')).toHaveValue('Tôi nên chuẩn bị gì cho lần tái khám?');
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click();
 await expect(page.getByRole('heading',{name:'Câu hỏi đang được chuyên gia xem lại'})).toBeVisible();
 await expect(page.locator('main')).not.toContainText('SECRET_UNAPPROVED_DRAFT');
 await expect(page.locator('main').getByRole('link',{name:'Lịch sử tư vấn'})).toHaveAttribute('href','/my/reviews');
});
test('patient Q&A renders answer and source without admin settings',async({page})=>{
 await page.route('**/v1/auth/me',r=>r.fulfill({json:user}));
 await page.route('**/v1/query',r=>r.fulfill({json:{status:'answered',answer:'Mang theo nhật ký của bạn.',contexts:[{file_name:'Tài liệu tham khảo',page:2}]}}));
 await page.goto('/api-playground');
 await page.getByLabel('Câu hỏi của bạn').fill('Chuẩn bị tái khám thế nào?');
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click();
 await expect(page.getByText('Mang theo nhật ký của bạn.')).toBeVisible();
 await page.getByText('Xem tài liệu tham khảo',{exact:true}).click();
 await expect(page.getByText('Tài liệu tham khảo · trang 2')).toBeVisible();
 await expect(page.locator('main')).not.toContainText(/top_k|prompt_version|WHO-RAG Infrastructure/);
});
