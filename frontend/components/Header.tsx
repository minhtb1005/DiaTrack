"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useState } from "react";
import { HeartPulse, Menu, X, LogOut } from "lucide-react";
import ThemeToggle from "./ThemeToggle";

export default function Header(){
 const {user,loading,logout,isExpert,isAdmin}=useAuth();
 const pathname=usePathname();const router=useRouter();const [open,setOpen]=useState(false);
 const items=user ? [{href:'/tracker',label:'Sổ đường huyết'},{href:'/medications',label:'Lịch thuốc'},{href:'/hoc',label:'Bài học'},{href:'/previsit',label:'Tái khám'}] : [{href:'/#cach-su-dung',label:'Cách sử dụng'},{href:'/hoc',label:'Bài học'}];
 const more=user ? [{href:'/api-playground',label:'Hỏi đáp'},{href:'/my/reviews',label:'Lịch sử tư vấn'},{href:'/settings',label:'Cài đặt'},...(isExpert||isAdmin?[{href:'/expert/patients',label:'Bệnh nhân'},{href:'/expert/queue',label:'Cần duyệt'},{href:'/monitor/guidelines',label:'Tài liệu chuyên môn'}]:[]),...(isAdmin?[{href:'/admin/users',label:'Quản lý tài khoản'},{href:'/admin/tracing',label:'Nhật ký hệ thống'},{href:'/admin/prompts',label:'Cấu hình trợ lý'},{href:'/admin/triage',label:'Theo dõi phân luồng'}]:[])] : [];
 const link=(item:{href:string;label:string})=><Link key={item.href} href={item.href} aria-current={pathname===item.href?'page':undefined} className={pathname===item.href?'nav-link active':'nav-link'} onClick={()=>setOpen(false)}>{item.label}</Link>;
 return <header className="site-header"><a href="#main-content" className="skip-link">Đến nội dung chính</a><div className="header-inner"><Link href="/" className="brand" aria-label="DiaTrack — Trang chủ"><span className="brand-icon"><HeartPulse aria-hidden size={25}/></span><span>DiaTrack<span className="brand-sub">Cùng bạn mỗi ngày</span></span></Link>
 <nav aria-label="Điều hướng chính" className="desktop-nav">{items.map(link)}{more.length>0&&<details className="nav-more"><summary>Thêm</summary><div>{more.map(link)}</div></details>}</nav>
 <div className="header-actions"><ThemeToggle/>{loading?<span role="status">Đang tải…</span>:user?<button className="account-exit" aria-label="Đăng xuất" onClick={async()=>{await logout();router.push('/login');}}><LogOut aria-hidden size={18}/><span>Đăng xuất</span></button>:<Link href="/login" className="login-link">Đăng nhập</Link>}<button className="menu-toggle" aria-label={open?'Đóng menu':'Mở menu'} aria-expanded={open} aria-controls="mobile-navigation" onClick={()=>setOpen(!open)}>{open?<X aria-hidden/>:<Menu aria-hidden/>}</button></div></div>
 {open&&<nav id="mobile-navigation" aria-label="Điều hướng di động" className="mobile-nav">{[...items,...more].map(link)}</nav>}</header>;
}