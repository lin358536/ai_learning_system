# 智途校园 - 邮件发送服务
"""
独立的邮件模块，支持多种场景的邮件通知：
- 简历发送
- 二课推荐通知
- 课表更新提醒

所有需要发邮件的地方统一调用此模块。
"""

import io
import json
import re
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr, formatdate

from app.core.config import get_settings


class EmailService:
    """邮件发送服务"""

    def __init__(self):
        settings = get_settings()
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD

    def _create_connection(self) -> smtplib.SMTP_SSL:
        """创建SMTP SSL连接"""
        conn = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
        conn.login(self.smtp_user, self.smtp_password)
        return conn

    def _send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        cc: list[str] | None = None,
        attachments: list[tuple[str, bytes]] | None = None,
    ) -> bool:
        """
        发送HTML邮件（底层方法）

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_body: HTML格式邮件正文
            cc: 抄送列表（可选）
            attachments: 附件列表，每项为 (文件名, 文件bytes)（可选）

        Returns:
            是否发送成功
        """
        if not self.smtp_host or not self.smtp_user:
            print("[email] SMTP未配置，跳过发送")
            return False

        # 有附件时用 mixed，纯HTML用 alternative
        if attachments:
            msg = MIMEMultipart("mixed")
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(html_body, "html", "utf-8"))
            msg.attach(alt)
            for filename, file_bytes in attachments:
                part = MIMEApplication(file_bytes, Name=filename)
                part["Content-Disposition"] = f'attachment; filename="{filename}"'
                msg.attach(part)
        else:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        msg["Subject"] = subject
        msg["From"] = formataddr(("XIAOTU AI", self.smtp_user))
        msg["To"] = to_email
        msg["Date"] = formatdate(localtime=True)
        if cc:
            msg["Cc"] = ", ".join(cc)

        try:
            conn = self._create_connection()
            recipients = [to_email] + (cc or [])
            conn.sendmail(self.smtp_user, recipients, msg.as_string())
            conn.quit()
            print(f"[email] 邮件发送成功 -> {to_email} | 主题: {subject}")
            return True
        except Exception as e:
            print(f"[email] 邮件发送失败: {e}")
            traceback.print_exc()
            return False

    @staticmethod
    def markdown_to_docx(resume_markdown: str, title: str = "简历") -> bytes:
        """
        将Markdown格式的简历文本转换为Word (.docx) 文件字节流

        Args:
            resume_markdown: AI生成的Markdown简历文本
            title: 简历标题（用于Word文档标题）

        Returns:
            docx文件的bytes
        """
        from docx import Document
        from docx.shared import Pt, RGBColor, Inches, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        doc = Document()

        # ── 页面设置（A4）──
        section = doc.sections[0]
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)

        # ── 默认字体 ──
        doc.styles["Normal"].font.name = "微软雅黑"
        doc.styles["Normal"].font.size = Pt(10.5)
        doc.styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

        def add_heading(text: str, level: int):
            """添加标题段落"""
            para = doc.add_paragraph()
            run = para.add_run(text)
            run.bold = True
            if level == 1:
                run.font.size = Pt(16)
                run.font.color.rgb = RGBColor(0x2d, 0x37, 0x48)
                para.paragraph_format.space_before = Pt(12)
                para.paragraph_format.space_after = Pt(6)
                # 下边框
                pBdr = OxmlElement("w:pBdr")
                bottom = OxmlElement("w:bottom")
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "6")
                bottom.set(qn("w:space"), "1")
                bottom.set(qn("w:color"), "4299E1")
                pBdr.append(bottom)
                para._p.pPr.append(pBdr)
            elif level == 2:
                run.font.size = Pt(13)
                run.font.color.rgb = RGBColor(0x2d, 0x37, 0x48)
                para.paragraph_format.space_before = Pt(10)
                para.paragraph_format.space_after = Pt(4)
                pBdr = OxmlElement("w:pBdr")
                bottom = OxmlElement("w:bottom")
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "4")
                bottom.set(qn("w:space"), "1")
                bottom.set(qn("w:color"), "667EEA")
                pBdr.append(bottom)
                para._p.pPr.append(pBdr)
            run.font.name = "微软雅黑"
            run._r.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

        def add_bullet(text: str):
            """添加列表项"""
            para = doc.add_paragraph(style="List Bullet")
            # 处理行内加粗
            parts = re.split(r"\*\*(.+?)\*\*", text)
            for i, part in enumerate(parts):
                run = para.add_run(part)
                run.bold = (i % 2 == 1)
                run.font.size = Pt(10.5)
                run.font.name = "微软雅黑"
                run._r.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
            para.paragraph_format.space_after = Pt(2)

        def add_normal(text: str):
            """添加普通段落，支持行内加粗"""
            para = doc.add_paragraph()
            parts = re.split(r"\*\*(.+?)\*\*", text)
            for i, part in enumerate(parts):
                run = para.add_run(part)
                run.bold = (i % 2 == 1)
                run.font.size = Pt(10.5)
                run.font.name = "微软雅黑"
                run._r.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
            para.paragraph_format.space_after = Pt(3)

        # ── 解析 Markdown 逐行处理 ──
        lines = resume_markdown.strip().split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("### "):
                add_heading(stripped[4:], level=2)
            elif stripped.startswith("## "):
                add_heading(stripped[3:], level=1)
            elif stripped.startswith("# "):
                add_heading(stripped[2:], level=1)
            elif stripped.startswith("- "):
                add_bullet(stripped[2:])
            else:
                add_normal(stripped)

        # ── 写到内存字节流 ──
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def send_resume(
        self,
        to_email: str,
        resume_data: dict,
        username: str = "同学",
    ) -> bool:
        """
        发送简历邮件

        Args:
            to_email: 收件人邮箱
            resume_data: 简历数据（AI生成的JSON结构）
            username: 用户称呼

        Returns:
            是否发送成功
        """
        title = resume_data.get("title", "我的简历")
        basic = resume_data.get("basic", {})
        skills = resume_data.get("skills", [])
        experience = resume_data.get("experience", [])
        certifications = resume_data.get("certifications", [])
        summary = resume_data.get("summary", "")

        # 构建经历HTML
        exp_html = ""
        for exp in experience:
            exp_html += f"""
            <div style="margin-bottom: 16px; padding-left: 12px; border-left: 3px solid #667eea;">
                <div style="font-weight: bold; color: #2d3748; font-size: 15px;">{exp.get('name', '')}</div>
                <div style="color: #718096; font-size: 13px;">{exp.get('role', '')} | {exp.get('duration', '')}</div>
                <div style="color: #4a5568; font-size: 14px; margin-top: 4px;">{exp.get('description', '')}</div>
            </div>
            """

        # 构建技能标签
        skills_html = "".join(
            f'<span style="display: inline-block; background: #ebf4ff; color: #3182ce; '
            f'padding: 4px 12px; border-radius: 12px; font-size: 13px; margin: 3px;">{s}</span>'
            for s in skills
        )

        # 构建证书列表
        cert_html = "".join(f"<li style='color: #4a5568; font-size: 14px;'>{c}</li>" for c in certifications)

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>body {{ font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; margin: 0; padding: 20px; background: #f7fafc; }}</style>
        </head>
        <body>
            <div style="max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

                <!-- 头部 -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px; text-align: center;">
                    <div style="font-size: 13px; color: rgba(255,255,255,0.8); letter-spacing: 4px; margin-bottom: 8px;">XIAOTU AI</div>
                    <div style="font-size: 24px; font-weight: bold; color: #ffffff;">{title}</div>
                </div>

                <!-- 基本信息 -->
                <div style="padding: 28px 32px; border-bottom: 1px solid #edf2f7;">
                    <div style="font-size: 12px; color: #a0aec0; letter-spacing: 2px; margin-bottom: 12px;">BASIC INFO</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 14px; color: #4a5568;">
                        <div><b>姓名：</b>{basic.get('name', username)}</div>
                        <div><b>学校：</b>{basic.get('school', '')}</div>
                        <div><b>专业：</b>{basic.get('major', '')}</div>
                        <div><b>学历：</b>{basic.get('education', '')}</div>
                        <div><b>毕业年份：</b>{basic.get('graduation_year', '')}</div>
                        <div><b>电话：</b>{basic.get('phone', '')}</div>
                        <div style="grid-column: span 2;"><b>邮箱：</b>{basic.get('email', to_email)}</div>
                    </div>
                </div>

                <!-- 个人总结 -->
                <div style="padding: 28px 32px; border-bottom: 1px solid #edf2f7;">
                    <div style="font-size: 12px; color: #a0aec0; letter-spacing: 2px; margin-bottom: 12px;">SUMMARY</div>
                    <div style="font-size: 14px; color: #4a5568; line-height: 1.8;">{summary}</div>
                </div>

                <!-- 技能 -->
                <div style="padding: 28px 32px; border-bottom: 1px solid #edf2f7;">
                    <div style="font-size: 12px; color: #a0aec0; letter-spacing: 2px; margin-bottom: 12px;">SKILLS</div>
                    <div>{skills_html if skills_html else '<span style="color:#a0aec0;">暂无</span>'}</div>
                </div>

                <!-- 项目经历 -->
                <div style="padding: 28px 32px; border-bottom: 1px solid #edf2f7;">
                    <div style="font-size: 12px; color: #a0aec0; letter-spacing: 2px; margin-bottom: 12px;">EXPERIENCE</div>
                    {exp_html if exp_html else '<div style="color:#a0aec0; font-size:14px;">暂无</div>'}
                </div>

                <!-- 证书 -->
                <div style="padding: 28px 32px; border-bottom: 1px solid #edf2f7;">
                    <div style="font-size: 12px; color: #a0aec0; letter-spacing: 2px; margin-bottom: 12px;">CERTIFICATIONS</div>
                    <ul style="padding-left: 20px; margin: 0;">
                        {cert_html if cert_html else '<li style="color:#a0aec0;">暂无</li>'}
                    </ul>
                </div>

                <!-- 页脚 -->
                <div style="padding: 20px 32px; background: #f7fafc; text-align: center;">
                    <div style="font-size: 12px; color: #a0aec0;">
                        此简历由 <b style="color: #667eea;">小途AI学习管家</b> 智能生成
                    </div>
                    <div style="font-size: 11px; color: #cbd5e0; margin-top: 4px;">
                        请在附件或上方内容中查看您的简历信息
                    </div>
                </div>

            </div>
        </body>
        </html>
        """

        subject = f"你的简历已生成 - {title}"
        return self._send(to_email, subject, html_body)

    def send_notification(
        self,
        to_email: str,
        title: str,
        content: str,
        highlight: str = "",
    ) -> bool:
        """
        通用通知邮件（二课推荐、课表提醒等）

        Args:
            to_email: 收件人邮箱
            title: 通知标题
            content: 通知正文（纯文本，会自动转HTML）
            highlight: 重点内容（加粗显示，可选）

        Returns:
            是否发送成功
        """
        # 纯文本换行转HTML段落
        paragraphs = content.strip().split("\n")
        body_html = "".join(
            f"<p style='margin: 8px 0; color: #4a5568; font-size: 14px; line-height: 1.8;'>{p}</p>"
            for p in paragraphs if p.strip()
        )

        highlight_html = ""
        if highlight:
            highlight_html = f"""
            <div style="background: #ebf8ff; border-left: 4px solid #4299e1; padding: 16px; margin-bottom: 20px; border-radius: 4px;">
                <div style="font-size: 14px; color: #2b6cb0; line-height: 1.8;">{highlight}</div>
            </div>
            """

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>body {{ font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; margin: 0; padding: 20px; background: #f7fafc; }}</style>
        </head>
        <body>
            <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

                <div style="background: linear-gradient(135deg, #4299e1 0%, #667eea 100%); padding: 28px; text-align: center;">
                    <div style="font-size: 13px; color: rgba(255,255,255,0.8); letter-spacing: 4px; margin-bottom: 8px;">XIAOTU AI</div>
                    <div style="font-size: 20px; font-weight: bold; color: #ffffff;">{title}</div>
                </div>

                <div style="padding: 28px 32px;">
                    {highlight_html}
                    {body_html}
                </div>

                <div style="padding: 20px 32px; background: #f7fafc; text-align: center;">
                    <div style="font-size: 12px; color: #a0aec0;">
                        此通知由 <b style="color: #667eea;">小途AI学习管家</b> 自动发送
                    </div>
                </div>

            </div>
        </body>
        </html>
        """

        subject = f"[小途管家] {title}"
        return self._send(to_email, subject, html_body)

    def send_activity_recommend(
        self,
        to_email: str,
        username: str,
        activities: list[dict],
    ) -> bool:
        """
        二课活动推荐邮件

        Args:
            to_email: 收件人邮箱
            username: 用户称呼
            activities: 活动列表，每个活动包含 title, time, location, points, description

        Returns:
            是否发送成功
        """
        items_html = ""
        for act in activities:
            items_html += f"""
            <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                <div style="font-weight: bold; color: #2d3748; font-size: 15px; margin-bottom: 8px;">{act.get('title', '')}</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 13px; color: #718096;">
                    <div>时间：{act.get('time', '待定')}</div>
                    <div>地点：{act.get('location', '待定')}</div>
                    <div>积分：{act.get('points', '')} 分</div>
                </div>
                <div style="font-size: 13px; color: #4a5568; margin-top: 8px; line-height: 1.6;">{act.get('description', '')}</div>
            </div>
            """

        content = f"你好，{username}！根据你的专业和学习方向，小途为你推荐以下二课活动："
        highlight = f"共 {len(activities)} 个推荐活动"

        return self.send_notification(
            to_email=to_email,
            title="二课活动推荐",
            content=content + items_html,
            highlight=highlight,
        )

    def send_resume_text(
        self,
        to_email: str,
        resume_markdown: str,
        username: str = "同学",
        resume_title: str = "我的简历",
    ) -> bool:
        """
        发送简历邮件（HTML正文预览 + Word附件可编辑）

        Args:
            to_email: 收件人邮箱
            resume_markdown: 简历Markdown文本
            username: 用户称呼
            resume_title: 简历标题（用于邮件标题和Word文件名）

        Returns:
            是否发送成功
        """
        # ── 1. 生成Word附件 ──
        try:
            docx_bytes = self.markdown_to_docx(resume_markdown, title=resume_title)
            safe_title = re.sub(r'[\\/:*?"<>|]', "_", resume_title)
            attachments = [(f"{safe_title}.docx", docx_bytes)]
            print(f"[email] Word简历生成成功，大小: {len(docx_bytes)} bytes")
        except Exception as e:
            print(f"[email] Word生成失败，降级为纯HTML邮件: {e}")
            traceback.print_exc()
            attachments = None

        # ── 2. Markdown → HTML预览 ──
        lines = resume_markdown.strip().split("\n")
        html_parts = []
        in_list = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                continue

            if stripped.startswith("### "):
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                html_parts.append(
                    f"<div style='font-size:15px;font-weight:bold;color:#2d3748;"
                    f"margin:20px 0 8px;padding-bottom:5px;"
                    f"border-bottom:2px solid #667eea;'>{stripped[4:]}</div>"
                )
            elif stripped.startswith("## "):
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                html_parts.append(
                    f"<div style='font-size:17px;font-weight:bold;color:#1a202c;"
                    f"margin:22px 0 10px;padding-bottom:6px;"
                    f"border-bottom:2px solid #4299e1;'>{stripped[3:]}</div>"
                )
            elif stripped.startswith("# "):
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                html_parts.append(
                    f"<div style='font-size:20px;font-weight:bold;color:#1a202c;"
                    f"margin:0 0 16px;text-align:center;'>{stripped[2:]}</div>"
                )
            elif stripped.startswith("- "):
                if not in_list:
                    html_parts.append("<ul style='padding-left:20px;margin:6px 0;'>")
                    in_list = True
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', stripped[2:])
                html_parts.append(
                    f"<li style='color:#4a5568;font-size:14px;line-height:1.8;margin-bottom:3px;'>{text}</li>"
                )
            else:
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', stripped)
                html_parts.append(
                    f"<div style='color:#4a5568;font-size:14px;line-height:1.8;margin:3px 0;'>{text}</div>"
                )

        if in_list:
            html_parts.append("</ul>")

        resume_html = "\n".join(html_parts)

        attach_tip = (
            "<div style='background:#ebf8ff;border-left:4px solid #4299e1;padding:12px 16px;"
            "border-radius:4px;margin-bottom:20px;font-size:13px;color:#2b6cb0;'>"
            "📎 <b>Word简历已作为附件发送</b>，请下载附件在Word中直接编辑修改后投递。"
            "</div>"
        ) if attachments else ""

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>body {{ font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; margin: 0; padding: 20px; background: #f7fafc; }}</style>
        </head>
        <body>
            <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px; text-align: center;">
                    <div style="font-size: 13px; color: rgba(255,255,255,0.8); letter-spacing: 4px; margin-bottom: 8px;">XIAOTU AI</div>
                    <div style="font-size: 22px; font-weight: bold; color: #ffffff;">智能简历</div>
                    <div style="font-size: 13px; color: rgba(255,255,255,0.7); margin-top: 6px;">由小途AI学习管家生成</div>
                </div>

                <div style="padding: 28px 32px;">
                    {attach_tip}
                    {resume_html}
                </div>

                <div style="padding: 20px 32px; background: #f7fafc; text-align: center;">
                    <div style="font-size: 12px; color: #a0aec0;">
                        此简历由 <b style="color: #667eea;">小途AI学习管家</b> 智能生成，仅供参考
                    </div>
                    <div style="font-size: 11px; color: #cbd5e0; margin-top: 4px;">
                        如需修改，请编辑附件中的Word文件，或在系统中重新生成
                    </div>
                </div>

            </div>
        </body>
        </html>
        """

        subject = f"[小途管家] 你的AI简历已生成 — {resume_title}"
        return self._send(to_email, subject, html_body, attachments=attachments)

    def send_schedule_remind(
        self,
        to_email: str,
        username: str,
        updates: list[dict],
    ) -> bool:
        """
        课表更新提醒邮件

        Args:
            to_email: 收件人邮箱
            username: 用户称呼
            updates: 更新列表，每个包含 course_name, old_time, new_time, old_location, new_location

        Returns:
            是否发送成功
        """
        items_html = ""
        for u in updates:
            items_html += f"""
            <div style="background: #fffbeb; border: 1px solid #fbd38d; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                <div style="font-weight: bold; color: #744210; font-size: 15px;">{u.get('course_name', '')}</div>
                <div style="font-size: 13px; color: #975a16; margin-top: 6px;">
                    时间：{u.get('old_time', '')} <span style="color:#c05621;">→</span> {u.get('new_time', '')}<br>
                    地点：{u.get('old_location', '')} <span style="color:#c05621;">→</span> {u.get('new_location', '')}
                </div>
            </div>
            """

        content = f"你好，{username}！你的课表有以下更新，请注意查看："
        highlight = f"{len(updates)} 门课程有变动"

        return self.send_notification(
            to_email=to_email,
            title="课表更新提醒",
            content=content + items_html,
            highlight=highlight,
        )


# 全局单例
_email_service = None


def get_email_service() -> EmailService:
    """获取邮件服务单例"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
