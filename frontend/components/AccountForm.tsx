"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { HeartPulse } from "lucide-react";

export default function AccountForm({registering=false}:{registering?:boolean}) {
 const auth=useAuth(); const router=useRouter();
 const [username,setUsername]=useState('');const [password,setPassword]=useState('');
 const [fullName,setFullName]=useState('');const [email,setEmail]=useState('');
 const [diabetesType,setDiabetesType]=useState<"type1"|"type2"|"unknown">("unknown");
 const [visible,setVisible]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function submit(e:React.FormEvent){e.preventDefault();if(busy)return;setBusy(true);setError('');try{
  if(registering){await auth.register({username:username.trim(),password,full_name:fullName.trim()||undefined,email:email.trim()||undefined,diabetes_type:diabetesType});router.push('/onboarding/voice');}
  else{await auth.login(username.trim(),password);router.push('/tracker');}
 }catch{setError(registering?'Chưa tạo được tài khoản. Tên đăng nhập có thể đã được sử dụng. Bạn hãy kiểm tra thông tin và thử lại.':'Chưa đăng nhập được. Hãy kiểm tra tên đăng nhập, mật khẩu và kết nối, rồi thử lại.');}finally{setBusy(false);}}
 return <div className="account-layout"><div className="account-intro"><HeartPulse size={42} aria-hidden/><p className="eyebrow mt-6">CÙNG BẠN MỖI NGÀY</p><h1>{registering?'Bắt đầu một thói quen chăm sóc bản thân.':'Chào bạn, mình tiếp tục nhé.'}</h1><p>Ghi lại một chỉ số. Nhớ một lịch thuốc. Chuẩn bị thêm một chút cho lần gặp bác sĩ.</p></div><Card className="p-6 sm:p-9"><h2 className="text-2xl font-semibold">{registering?'Tạo tài khoản':'Đăng nhập'}</h2><p className="mt-2 text-slate-600 dark:text-slate-300">{registering?'Các mục có dấu * là bắt buộc.':'Sử dụng tài khoản DiaTrack của bạn.'}</p>
 <form onSubmit={submit} className="mt-6 space-y-5" aria-busy={busy}>
 <div><label htmlFor="account-username" className="block font-semibold mb-2">Tên đăng nhập{registering?' *':''}</label><Input id="account-username" autoComplete="username" autoCapitalize="none" spellCheck={false} value={username} onChange={e=>setUsername(e.target.value)} required minLength={registering?3:undefined} maxLength={50} pattern={registering?'[a-zA-Z0-9_.\\-]+':undefined} aria-describedby={registering?'username-hint':undefined}/>{registering&&<p id="username-hint" className="text-sm mt-2">Từ 3 ký tự; dùng chữ không dấu, số, dấu chấm, gạch ngang hoặc gạch dưới.</p>}</div>
 {registering&&<><div><label htmlFor="account-name" className="block font-semibold mb-2">Họ và tên (không bắt buộc)</label><Input id="account-name" autoComplete="name" value={fullName} onChange={e=>setFullName(e.target.value)}/></div><div><label htmlFor="account-email" className="block font-semibold mb-2">Email (không bắt buộc)</label><Input id="account-email" type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)}/></div><div><label htmlFor="diabetes-type" className="block font-semibold mb-2">Loại đái tháo đường theo hồ sơ của bạn</label><select id="diabetes-type" className="w-full min-h-12 rounded-lg border px-3" value={diabetesType} onChange={e=>setDiabetesType(e.target.value as typeof diabetesType)}><option value="unknown">Chưa rõ hoặc chưa được xác nhận</option><option value="type2">Týp 2</option><option value="type1">Týp 1</option></select><p className="text-sm mt-2">Đây là thông tin bạn tự khai báo, không phải chẩn đoán. Tính năng tư vấn chỉ dành cho người đã biết mình mắc týp 2.</p></div></>}
 <div><label htmlFor="account-password" className="block font-semibold mb-2">Mật khẩu{registering?' *':''}</label><Input id="account-password" type={visible?'text':'password'} autoComplete={registering?'new-password':'current-password'} value={password} onChange={e=>setPassword(e.target.value)} required minLength={registering?6:undefined} maxLength={100}/>{registering&&<p className="text-sm mt-2">Ít nhất 6 ký tự.</p>}<label className="mt-2 flex min-h-12 items-center gap-3 cursor-pointer"><input type="checkbox" checked={visible} onChange={e=>setVisible(e.target.checked)}/>Hiện mật khẩu</label></div>
 {error&&<p role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}
 <Button className="w-full" size="lg" type="submit" disabled={busy}>{busy?'Đang xử lý…':registering?'Tạo tài khoản':'Đăng nhập'}</Button></form>
 <p className="mt-6">{registering?'Bạn đã có tài khoản?':'Bạn chưa có tài khoản?'} <Link className="underline font-semibold inline-flex min-h-12 items-center" href={registering?'/login':'/register'}>{registering?'Đăng nhập':'Tạo tài khoản'}</Link></p></Card></div>;
}
