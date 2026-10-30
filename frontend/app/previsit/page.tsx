"use client";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import PrevisitView from "@/components/PrevisitView";
import { Card } from "@/components/ui/card";

export default function PrevisitPage(){
  const { user } = useAuth();
  if(!user) return <Card className="p-8 text-center">Cần đăng nhập <Link href="/login" className="underline">Đăng nhập</Link></Card>;
  return <PrevisitView patientId={user.id} patientName={user.username} title="Chuẩn bị cho lần tái khám" subtitle="Xem lại chỉ số và tạo bản tóm tắt để trao đổi với bác sĩ." />;
}
