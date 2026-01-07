import streamlit as st
import pandas as pd
from datetime import datetime
import json
import base64
from supabase import create_client, Client
import os
import re
import hashlib

# 设置页面配置
st.set_page_config(
    page_title="揭阳市医学会临床药学分会数据收集系统",
    page_icon="💊",
    layout="wide"
)

# ==================== Supabase配置 ====================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("⚠️ 数据库配置错误，请联系管理员")
    st.stop()

# ==================== 文件名清理函数 ====================

def chinese_to_pinyin_simple(text):
    """简单的中文转拼音方法（使用哈希）"""
    cleaned = re.sub(r'[^\w]', '', text)
    ascii_part = re.sub(r'[^\x00-\x7F]', '', cleaned)
    
    if len(ascii_part) < len(cleaned):
        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_str = hash_obj.hexdigest()[:8]
        if ascii_part:
            return f"{ascii_part}_{hash_str}"
        else:
            return f"unit_{hash_str}"
    else:
        return ascii_part if ascii_part else "unit"

def sanitize_path(path_str):
    """清理路径字符串"""
    safe_str = chinese_to_pinyin_simple(path_str)
    safe_str = re.sub(r'[^\w\-]', '_', safe_str)
    safe_str = re.sub(r'_+', '_', safe_str)
    safe_str = safe_str.strip('_')
    
    if len(safe_str) > 50:
        safe_str = safe_str[:50]
    
    if not safe_str:
        safe_str = f"file_{datetime.now().strftime('%Y%m%d')}"
    
    return safe_str

def generate_safe_filename(original_name, prefix="file"):
    """生成安全的文件名（带版本号）"""
    ext = os.path.splitext(original_name)[1]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:17]
    return f"{prefix}_{timestamp}{ext}"

def get_unit_safe_name(unit_name):
    """为单位名称生成安全的文件夹名"""
    unit_hash = hashlib.md5(unit_name.encode('utf-8')).hexdigest()[:8]
    safe_name = sanitize_path(unit_name)
    return f"{safe_name}_{unit_hash}"

def validate_phone(phone):
    """验证手机号是否为11位数字"""
    if not phone:
        return False
    phone = phone.replace(" ", "").replace("-", "")
    return len(phone) == 11 and phone.isdigit()

def file_to_base64(file):
    """将文件转换为base64字符串"""
    return base64.b64encode(file.getvalue()).decode()

def base64_to_file(b64_string, filename, file_type):
    """将base64字符串转换回文件对象"""
    file_bytes = base64.b64decode(b64_string)
    return type('UploadedFile', (), {
        'name': filename,
        'type': file_type,
        'getvalue': lambda: file_bytes
    })()

# ==================== 数据库操作函数 ====================

def save_to_supabase(table_name, data):
    """保存数据到Supabase"""
    try:
        result = supabase.table(table_name).insert(data).execute()
        return True, result
    except Exception as e:
        error_msg = str(e)
        if "row-level security policy" in error_msg.lower() or "violates" in error_msg.lower():
            return False, "数据库权限配置错误，请联系管理员检查RLS策略"
        return False, error_msg

def update_supabase(table_name, data, match_field, match_value):
    """更新Supabase数据"""
    try:
        result = supabase.table(table_name).update(data).eq(match_field, match_value).execute()
        return True, result
    except Exception as e:
        error_msg = str(e)
        if "row-level security policy" in error_msg.lower() or "violates" in error_msg.lower():
            return False, "数据库权限配置错误，请联系管理员检查RLS策略"
        return False, error_msg

def get_from_supabase(table_name, unit_name=None):
    """从Supabase获取数据"""
    try:
        if unit_name:
            result = supabase.table(table_name).select("*").eq("unit_name", unit_name).execute()
        else:
            result = supabase.table(table_name).select("*").execute()
        return result.data
    except Exception as e:
        st.error(f"读取数据失败: {str(e)}")
        return []

def delete_from_supabase(table_name, record_id):
    """从Supabase删除数据"""
    try:
        result = supabase.table(table_name).delete().eq("id", record_id).execute()
        return True, result
    except Exception as e:
        return False, str(e)

def upload_file_to_storage(file, bucket_name, file_path):
    """上传文件到Supabase Storage（不覆盖，使用版本号）"""
    try:
        file_bytes = file.getvalue()
        file_path = file_path.encode('ascii', 'ignore').decode('ascii')
        
        result = supabase.storage.from_(bucket_name).upload(
            file_path, 
            file_bytes,
            {"content-type": file.type, "upsert": "false"}
        )
        
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return True, public_url
    except Exception as e:
        return False, str(e)

def delete_file_from_storage(bucket_name, file_path):
    """从Supabase Storage删除文件"""
    try:
        if file_path.startswith('http'):
            parts = file_path.split('/storage/v1/object/public/' + bucket_name + '/')
            if len(parts) > 1:
                file_path = parts[1]
        
        result = supabase.storage.from_(bucket_name).remove([file_path])
        return True, result
    except Exception as e:
        return False, str(e)

# ==================== 待提交数据管理函数 ====================

def load_pending_data(table_name, unit_name):
    """从临时表加载待提交数据"""
    try:
        result = supabase.table(table_name).select("*").eq("unit_name", unit_name).execute()
        return result.data
    except Exception as e:
        return []

def save_pending_item(table_name, data):
    """保存单条待提交数据到临时表"""
    try:
        result = supabase.table(table_name).insert(data).execute()
        return True, result
    except Exception as e:
        return False, str(e)

def delete_pending_item(table_name, item_id):
    """从临时表删除单条数据"""
    try:
        result = supabase.table(table_name).delete().eq("id", item_id).execute()
        return True, result
    except Exception as e:
        return False, str(e)

def clear_pending_data(table_name, unit_name):
    """清空单位的所有待提交数据"""
    try:
        result = supabase.table(table_name).delete().eq("unit_name", unit_name).execute()
        return True, result
    except Exception as e:
        return False, str(e)

# ==================== 数据加载函数 ====================

def load_unit_summary(unit_name):
    """加载单位的年度总结数据"""
    data = get_from_supabase("work_summary", unit_name)
    return data[0] if data else None

def load_summary_documents(unit_name):
    """加载单位的所有年度总结文档"""
    try:
        result = supabase.table("summary_documents").select("*").eq("unit_name", unit_name).order("uploaded_at", desc=True).execute()
        return result.data
    except Exception as e:
        st.error(f"读取文档列表失败: {str(e)}")
        return []

def load_activities(table_name, unit_name):
    """加载活动数据"""
    return get_from_supabase(table_name, unit_name)

# ==================== 主程序 ====================

def main():
    st.title("💊 揭阳市医学会临床药学分会数据收集系统")
    st.markdown("---")
    
    # 单位信息
    st.header("📋 单位信息")
    
    st.info("💡 **重要提示：** 请各成员单位指定专人负责本单位信息的填报工作，确保数据准确性。填报过程中报错或有任何问题请联系学会秘书（黄晓杰，18318149900）。")
    
    unit_name = st.text_input(
        "请输入单位名称*", 
        placeholder="例如：揭阳市人民医院", 
        key="unit_name_input",
        help="请填写单位全称"
    )
    
    if not unit_name:
        st.warning("⚠️ 请先填写单位名称后再继续填报")
        return
    
    # 加载该单位的历史数据
    summary_data = load_unit_summary(unit_name)
    
    # 预填联系信息
    default_contact = summary_data.get('contact_person', '') if summary_data else ''
    default_phone = summary_data.get('contact_phone', '') if summary_data else ''
    
    contact_person = st.text_input(
        "联系人*", 
        value=default_contact, 
        placeholder="请输入联系人姓名",
        help="请填写负责本单位数据填报的联系人"
    )
    
    contact_phone = st.text_input(
        "联系电话*", 
        value=default_phone, 
        placeholder="请输入11位手机号码",
        max_chars=11,
        help="请输入11位手机号码"
    )
    
    # 验证手机号
    if contact_phone and not validate_phone(contact_phone):
        st.error("❌ 请输入正确的11位手机号码")
    
    # 显示转换后的路径（用于调试）
    with st.expander("🔍 调试信息（可选查看）"):
        safe_folder = get_unit_safe_name(unit_name)
        st.code(f"单位名称: {unit_name}\n文件夹路径: {safe_folder}")
    
    st.markdown("---")
    
    # 创建标签页
    tabs = st.tabs([
        "📄 年度总结与计划",
        "🎓 学术活动",
        "📢 科普活动",
        "🏆 技能竞赛",
        "🥇 获奖情况",
        "🔬 科研立项",
        "📚 论文发表",
        "📊 提交概览"
    ])
    
    # ========== 年度总结与计划 ==========
    with tabs[0]:
        st.subheader("2025年度总结与2026年计划")
        st.info("💡 提示：请将年度总结和计划合并为一个Word文档上传。支持上传多个版本，所有版本都会被保存。")
        
        # 显示已上传的文档列表
        uploaded_docs = load_summary_documents(unit_name)
        
        if uploaded_docs:
            st.success(f"✅ 您已上传 {len(uploaded_docs)} 个版本的年度总结与计划")
            with st.expander("📄 查看已上传的文档", expanded=True):
                for idx, doc in enumerate(uploaded_docs, 1):
                    col1, col2, col3 = st.columns([6, 2, 2])
                    
                    with col1:
                        st.write(f"**版本 {idx}**")
                        st.write(f"上传时间：{doc.get('uploaded_at', '未知')[:19]}")
                        st.write(f"原文件名：{doc.get('original_filename', '未知')}")
                        st.markdown(f"[📄 下载文档]({doc['document_url']})")
                    
                    with col2:
                        if idx == 1:
                            st.success("当前版本")
                    
                    with col3:
                        if st.button(f"🗑️ 删除", key=f"del_doc_{doc['id']}"):
                            file_success, _ = delete_file_from_storage("documents", doc['document_url'])
                            db_success, _ = delete_from_supabase("summary_documents", doc['id'])
                            
                            if file_success and db_success:
                                st.success("删除成功！")
                                st.rerun()
                            else:
                                st.error("删除失败，请重试")
                    
                    st.markdown("---")
        
        summary_plan_file = st.file_uploader(
            "上传年度总结与计划文档（Word文档）*",
            type=['doc', 'docx'],
            key="summary_plan",
            help="支持上传多次，每次上传都会保存为新版本"
        )
        
        if st.button("💾 上传年度总结与计划", key="save_summary_plan", type="primary"):
            if not contact_person or not contact_phone:
                st.error("❌ 请填写完整的联系人和联系电话")
            elif not validate_phone(contact_phone):
                st.error("❌ 请输入正确的11位手机号码")
            elif summary_plan_file:
                with st.spinner("正在上传文档..."):
                    try:
                        safe_filename = generate_safe_filename(summary_plan_file.name, prefix="summary")
                        safe_unit_folder = get_unit_safe_name(unit_name)
                        file_path = f"{safe_unit_folder}/summary/{safe_filename}"
                        
                        st.info(f"📁 上传路径: {file_path}")
                        
                        success, result = upload_file_to_storage(summary_plan_file, "documents", file_path)
                        
                        if success:
                            document_url = result
                            
                            doc_data = {
                                "unit_name": unit_name,
                                "document_url": document_url,
                                "original_filename": summary_plan_file.name,
                                "uploaded_at": datetime.now().isoformat()
                            }
                            doc_success, doc_result = save_to_supabase("summary_documents", doc_data)
                            
                            summary_update_data = {
                                "unit_name": unit_name,
                                "contact_person": contact_person,
                                "contact_phone": contact_phone,
                                "summary_url": document_url,
                                "updated_at": datetime.now().isoformat()
                            }
                            
                            existing = get_from_supabase("work_summary", unit_name)
                            if existing:
                                success, result = update_supabase("work_summary", summary_update_data, "unit_name", unit_name)
                            else:
                                success, result = save_to_supabase("work_summary", summary_update_data)
                            
                            if success and doc_success:
                                st.success("✅ 上传成功！文档已保存为新版本")
                                st.info(f"📄 原文件名：{summary_plan_file.name}")
                                st.rerun()
                            else:
                                st.error(f"❌ 数据库保存失败")
                        else:
                            st.error(f"❌ 文档上传失败: {result}")
                    except Exception as e:
                        st.error(f"❌ 上传过程出错: {str(e)}")
            else:
                st.warning("⚠️ 请选择要上传的文档")
    
    # ========== 学术活动 ==========
    with tabs[1]:
        st.subheader("学术活动登记")
        
        # 加载已提交的数据
        submitted_academic = load_activities("academic_activities", unit_name)
        
        # 显示已提交的活动
        if submitted_academic:
            st.success(f"✅ 您已提交 {len(submitted_academic)} 条学术活动")
            with st.expander("📋 查看已提交的学术活动", expanded=False):
                for idx, activity in enumerate(submitted_academic, 1):
                    st.markdown(f"### {idx}. {activity['activity_name']} ({activity['activity_date']})")
                    st.write(f"**简介：** {activity['description']}")
                    
                    image_urls = json.loads(activity.get('image_urls', '[]'))
                    if image_urls:
                        st.write(f"**图片：** {len(image_urls)}张")
                        cols = st.columns(min(len(image_urls), 3))
                        for img_idx, img_url in enumerate(image_urls):
                            with cols[img_idx % 3]:
                                try:
                                    st.image(img_url, use_container_width=True)
                                except:
                                    st.markdown(f"[🖼️ 查看图片]({img_url})")
                    
                    if st.button(f"🗑️ 删除此条记录", key=f"del_submitted_academic_{activity['id']}"):
                        success, _ = delete_from_supabase("academic_activities", activity['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
                        else:
                            st.error("删除失败，请重试")
                    st.markdown("---")
        
        # 从临时表加载待提交列表
        pending_academic = load_pending_data("pending_academic_activities", unit_name)
        
        # 显示待提交的活动
        if pending_academic:
            st.markdown("### 📝 待提交的学术活动")
            st.warning(f"⏳ 您有 {len(pending_academic)} 条待提交的学术活动，请点击下方按钮提交")
            
            for idx, activity in enumerate(pending_academic):
                with st.expander(f"⏳ {idx+1}. {activity['activity_name']} - {activity['activity_date']}", expanded=False):
                    st.write(f"**活动日期：** {activity['activity_date']}")
                    st.write(f"**活动名称：** {activity['activity_name']}")
                    st.write(f"**活动简介：** {activity['description']}")
                    
                    # 显示图片（从base64还原）
                    if activity.get('image_data'):
                        try:
                            image_info = json.loads(activity['image_data'])
                            if image_info:
                                st.write(f"**活动图片：** {len(image_info)}张")
                                cols = st.columns(min(len(image_info), 3))
                                for img_idx, img_data in enumerate(image_info):
                                    with cols[img_idx % 3]:
                                        try:
                                            img_bytes = base64.b64decode(img_data['data'])
                                            st.image(img_bytes, caption=f"图片 {img_idx+1}", use_container_width=True)
                                        except:
                                            pass
                        except:
                            pass
                    
                    if st.button(f"🗑️ 删除此条", key=f"del_pending_academic_{activity['id']}"):
                        success, _ = delete_pending_item("pending_academic_activities", activity['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
            
            # 添加提交全部按钮
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("💾 提交全部待提交内容", key="submit_all_pending_academic", type="primary", use_container_width=True):
                    with st.spinner("正在提交数据..."):
                        success_count = 0
                        safe_unit_folder = get_unit_safe_name(unit_name)
                        
                        for activity in pending_academic:
                            image_urls = []
                            
                            # 处理图片
                            if activity.get('image_data'):
                                try:
                                    image_info = json.loads(activity['image_data'])
                                    for img_idx, img_data in enumerate(image_info):
                                        # 从base64还原文件
                                        img_file = base64_to_file(
                                            img_data['data'], 
                                            img_data['name'], 
                                            img_data['type']
                                        )
                                        
                                        safe_filename = generate_safe_filename(img_file.name, prefix=f"academic_{img_idx}")
                                        safe_activity_name = sanitize_path(activity['activity_name'][:30])
                                        file_path = f"{safe_unit_folder}/academic/{safe_activity_name}/{safe_filename}"
                                        
                                        success, result = upload_file_to_storage(img_file, "images", file_path)
                                        if success:
                                            image_urls.append(result)
                                except Exception as e:
                                    st.warning(f"图片上传失败: {str(e)}")
                            
                            # 保存到正式表
                            data = {
                                "unit_name": unit_name,
                                "activity_date": activity['activity_date'],
                                "activity_name": activity['activity_name'],
                                "description": activity['description'],
                                "image_urls": json.dumps(image_urls),
                                "created_at": datetime.now().isoformat()
                            }
                            success, result = save_to_supabase("academic_activities", data)
                            if success:
                                success_count += 1
                                # 从临时表删除
                                delete_pending_item("pending_academic_activities", activity['id'])
                        
                        if success_count == len(pending_academic):
                            st.success(f"✅ 成功提交{success_count}条学术活动记录！")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ 成功提交{success_count}条，共{len(pending_academic)}条")
            
            st.markdown("---")
        
        # 添加新活动表单
        with st.form(key="academic_form_new"):
            st.markdown("### ➕ 添加学术活动")
            
            col1, col2 = st.columns(2)
            with col1:
                activity_date = st.date_input("活动日期*")
            with col2:
                activity_name = st.text_input("活动名称*")
            
            activity_desc = st.text_area("活动简介*", height=100)
            
            activity_images = st.file_uploader(
                "上传活动图片（最多3张）",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="academic_images_new"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加到待提交", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并立即提交", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if activity_name and activity_desc:
                    if activity_images and len(activity_images) > 3:
                        st.error("❌ 最多只能上传3张图片")
                    else:
                        # 将图片转换为base64存储
                        image_data_list = []
                        if activity_images:
                            for img in activity_images:
                                image_data_list.append({
                                    'name': img.name,
                                    'type': img.type,
                                    'data': file_to_base64(img)
                                })
                        
                        if submit_and_continue:
                            # 保存到临时表
                            pending_data = {
                                "unit_name": unit_name,
                                "activity_date": str(activity_date),
                                "activity_name": activity_name,
                                "description": activity_desc,
                                "image_data": json.dumps(image_data_list) if image_data_list else None
                            }
                            success, result = save_pending_item("pending_academic_activities", pending_data)
                            if success:
                                st.success(f"✅ 已添加到待提交：{activity_name}")
                                st.info("💡 请点击上方【提交全部待提交内容】按钮完成提交，或继续添加更多活动")
                                st.rerun()
                            else:
                                st.error("❌ 保存失败，请重试")
                        
                        elif submit_final:
                            # 直接提交
                            with st.spinner("正在上传数据..."):
                                image_urls = []
                                safe_unit_folder = get_unit_safe_name(unit_name)
                                
                                if activity_images:
                                    for img_idx, img in enumerate(activity_images):
                                        safe_filename = generate_safe_filename(img.name, prefix=f"academic_{img_idx}")
                                        safe_activity_name = sanitize_path(activity_name[:30])
                                        file_path = f"{safe_unit_folder}/academic/{safe_activity_name}/{safe_filename}"
                                        
                                        success, result = upload_file_to_storage(img, "images", file_path)
                                        if success:
                                            image_urls.append(result)
                                
                                data = {
                                    "unit_name": unit_name,
                                    "activity_date": str(activity_date),
                                    "activity_name": activity_name,
                                    "description": activity_desc,
                                    "image_urls": json.dumps(image_urls),
                                    "created_at": datetime.now().isoformat()
                                }
                                success, result = save_to_supabase("academic_activities", data)
                                if success:
                                    st.success(f"✅ 成功提交1条学术活动记录！")
                                    st.rerun()
                                else:
                                    st.error("❌ 提交失败")
                else:
                    st.error("❌ 请填写所有必填项（标有*）")
    
    # ========== 科普活动 ========== 
    with tabs[2]:
        st.subheader("科普活动登记")
        
        submitted_popular = load_activities("popular_activities", unit_name)
        
        if submitted_popular:
            st.success(f"✅ 您已提交 {len(submitted_popular)} 条科普活动")
            with st.expander("📋 查看已提交的科普活动", expanded=False):
                for idx, activity in enumerate(submitted_popular, 1):
                    st.markdown(f"### {idx}. {activity['activity_name']} ({activity['activity_date']})")
                    st.write(f"**简介：** {activity['description']}")
                    
                    image_urls = json.loads(activity.get('image_urls', '[]'))
                    if image_urls:
                        st.write(f"**图片：** {len(image_urls)}张")
                        cols = st.columns(min(len(image_urls), 3))
                        for img_idx, img_url in enumerate(image_urls):
                            with cols[img_idx % 3]:
                                try:
                                    st.image(img_url, use_container_width=True)
                                except:
                                    st.markdown(f"[🖼️ 查看图片]({img_url})")
                    
                    if st.button(f"🗑️ 删除此条记录", key=f"del_submitted_popular_{activity['id']}"):
                        success, _ = delete_from_supabase("popular_activities", activity['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
                        else:
                            st.error("删除失败，请重试")
                    st.markdown("---")
        
        pending_popular = load_pending_data("pending_popular_activities", unit_name)
        
        if pending_popular:
            st.markdown("### 📝 待提交的科普活动")
            st.warning(f"⏳ 您有 {len(pending_popular)} 条待提交的科普活动")
            
            for idx, activity in enumerate(pending_popular):
                with st.expander(f"⏳ {idx+1}. {activity['activity_name']} - {activity['activity_date']}", expanded=False):
                    st.write(f"**活动日期：** {activity['activity_date']}")
                    st.write(f"**活动名称：** {activity['activity_name']}")
                    st.write(f"**活动简介：** {activity['description']}")
                    
                    if activity.get('image_data'):
                        try:
                            image_info = json.loads(activity['image_data'])
                            if image_info:
                                st.write(f"**活动图片：** {len(image_info)}张")
                                cols = st.columns(min(len(image_info), 3))
                                for img_idx, img_data in enumerate(image_info):
                                    with cols[img_idx % 3]:
                                        try:
                                            img_bytes = base64.b64decode(img_data['data'])
                                            st.image(img_bytes, caption=f"图片 {img_idx+1}", use_container_width=True)
                                        except:
                                            pass
                        except:
                            pass
                    
                    if st.button(f"🗑️ 删除此条", key=f"del_pending_popular_{activity['id']}"):
                        success, _ = delete_pending_item("pending_popular_activities", activity['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("💾 提交全部待提交内容", key="submit_all_pending_popular", type="primary", use_container_width=True):
                    with st.spinner("正在提交数据..."):
                        success_count = 0
                        safe_unit_folder = get_unit_safe_name(unit_name)
                        
                        for activity in pending_popular:
                            image_urls = []
                            
                            if activity.get('image_data'):
                                try:
                                    image_info = json.loads(activity['image_data'])
                                    for img_idx, img_data in enumerate(image_info):
                                        img_file = base64_to_file(img_data['data'], img_data['name'], img_data['type'])
                                        safe_filename = generate_safe_filename(img_file.name, prefix=f"popular_{img_idx}")
                                        safe_activity_name = sanitize_path(activity['activity_name'][:30])
                                        file_path = f"{safe_unit_folder}/popular/{safe_activity_name}/{safe_filename}"
                                        
                                        success, result = upload_file_to_storage(img_file, "images", file_path)
                                        if success:
                                            image_urls.append(result)
                                except:
                                    pass
                            
                            data = {
                                "unit_name": unit_name,
                                "activity_date": activity['activity_date'],
                                "activity_name": activity['activity_name'],
                                "description": activity['description'],
                                "image_urls": json.dumps(image_urls),
                                "created_at": datetime.now().isoformat()
                            }
                            success, result = save_to_supabase("popular_activities", data)
                            if success:
                                success_count += 1
                                delete_pending_item("pending_popular_activities", activity['id'])
                        
                        if success_count == len(pending_popular):
                            st.success(f"✅ 成功提交{success_count}条科普活动记录！")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ 成功提交{success_count}条")
            
            st.markdown("---")
        
        with st.form(key="popular_form_new"):
            st.markdown("### ➕ 添加科普活动")
            
            col1, col2 = st.columns(2)
            with col1:
                pop_date = st.date_input("活动日期*")
            with col2:
                pop_name = st.text_input("活动名称*")
            
            pop_desc = st.text_area("活动简介*", height=100)
            
            pop_images = st.file_uploader(
                "上传活动图片（最多3张）",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="popular_images_new"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加到待提交", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并立即提交", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if pop_name and pop_desc:
                    if pop_images and len(pop_images) > 3:
                        st.error("❌ 最多只能上传3张图片")
                    else:
                        image_data_list = []
                        if pop_images:
                            for img in pop_images:
                                image_data_list.append({
                                    'name': img.name,
                                    'type': img.type,
                                    'data': file_to_base64(img)
                                })
                        
                        if submit_and_continue:
                            pending_data = {
                                "unit_name": unit_name,
                                "activity_date": str(pop_date),
                                "activity_name": pop_name,
                                "description": pop_desc,
                                "image_data": json.dumps(image_data_list) if image_data_list else None
                            }
                            success, result = save_pending_item("pending_popular_activities", pending_data)
                            if success:
                                st.success(f"✅ 已添加到待提交：{pop_name}")
                                st.info("💡 请点击上方【提交全部待提交内容】按钮完成提交")
                                st.rerun()
                            else:
                                st.error("❌ 保存失败")
                        
                        elif submit_final:
                            with st.spinner("正在上传数据..."):
                                image_urls = []
                                safe_unit_folder = get_unit_safe_name(unit_name)
                                
                                if pop_images:
                                    for img_idx, img in enumerate(pop_images):
                                        safe_filename = generate_safe_filename(img.name, prefix=f"popular_{img_idx}")
                                        safe_activity_name = sanitize_path(pop_name[:30])
                                        file_path = f"{safe_unit_folder}/popular/{safe_activity_name}/{safe_filename}"
                                        
                                        success, result = upload_file_to_storage(img, "images", file_path)
                                        if success:
                                            image_urls.append(result)
                                
                                data = {
                                    "unit_name": unit_name,
                                    "activity_date": str(pop_date),
                                    "activity_name": pop_name,
                                    "description": pop_desc,
                                    "image_urls": json.dumps(image_urls),
                                    "created_at": datetime.now().isoformat()
                                }
                                success, result = save_to_supabase("popular_activities", data)
                                if success:
                                    st.success(f"✅ 成功提交1条科普活动记录！")
                                    st.rerun()
                else:
                    st.error("❌ 请填写所有必填项（标有*）")
    
    # ========== 技能竞赛 ==========
    with tabs[3]:
        st.subheader("技能竞赛登记")
        
        submitted_comps = load_activities("competitions", unit_name)
        
        if submitted_comps:
            st.success(f"✅ 您已提交 {len(submitted_comps)} 条技能竞赛")
            with st.expander("📋 查看已提交的技能竞赛", expanded=False):
                for idx, comp in enumerate(submitted_comps, 1):
                    st.markdown(f"### {idx}. {comp['competition_name']} ({comp['competition_date']})")
                    st.write(f"**简介：** {comp['description']}")
                    
                    image_urls = json.loads(comp.get('image_urls', '[]'))
                    if image_urls:
                        st.write(f"**图片：** {len(image_urls)}张")
                        cols = st.columns(min(len(image_urls), 3))
                        for img_idx, img_url in enumerate(image_urls):
                            with cols[img_idx % 3]:
                                try:
                                    st.image(img_url, use_container_width=True)
                                except:
                                    st.markdown(f"[🖼️ 查看图片]({img_url})")
                    
                    if st.button(f"🗑️ 删除此条记录", key=f"del_submitted_comp_{comp['id']}"):
                        success, _ = delete_from_supabase("competitions", comp['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
                        else:
                            st.error("删除失败，请重试")
                    st.markdown("---")
        
        pending_comps = load_pending_data("pending_competitions", unit_name)
        
        if pending_comps:
            st.markdown("### 📝 待提交的技能竞赛")
            st.warning(f"⏳ 您有 {len(pending_comps)} 条待提交的技能竞赛")
            
            for idx, comp in enumerate(pending_comps):
                with st.expander(f"⏳ {idx+1}. {comp['competition_name']} - {comp['competition_date']}", expanded=False):
                    st.write(f"**竞赛日期：** {comp['competition_date']}")
                    st.write(f"**竞赛名称：** {comp['competition_name']}")
                    st.write(f"**竞赛简介：** {comp['description']}")
                    
                    if comp.get('image_data'):
                        try:
                            image_info = json.loads(comp['image_data'])
                            if image_info:
                                st.write(f"**竞赛图片：** {len(image_info)}张")
                                cols = st.columns(min(len(image_info), 3))
                                for img_idx, img_data in enumerate(image_info):
                                    with cols[img_idx % 3]:
                                        try:
                                            img_bytes = base64.b64decode(img_data['data'])
                                            st.image(img_bytes, caption=f"图片 {img_idx+1}", use_container_width=True)
                                        except:
                                            pass
                        except:
                            pass
                    
                    if st.button(f"🗑️ 删除此条", key=f"del_pending_comp_{comp['id']}"):
                        success, _ = delete_pending_item("pending_competitions", comp['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("💾 提交全部待提交内容", key="submit_all_pending_comps", type="primary", use_container_width=True):
                    with st.spinner("正在提交数据..."):
                        success_count = 0
                        safe_unit_folder = get_unit_safe_name(unit_name)
                        
                        for comp in pending_comps:
                            image_urls = []
                            
                            if comp.get('image_data'):
                                try:
                                    image_info = json.loads(comp['image_data'])
                                    for img_idx, img_data in enumerate(image_info):
                                        img_file = base64_to_file(img_data['data'], img_data['name'], img_data['type'])
                                        safe_filename = generate_safe_filename(img_file.name, prefix=f"comp_{img_idx}")
                                        safe_comp_name = sanitize_path(comp['competition_name'][:30])
                                        file_path = f"{safe_unit_folder}/competition/{safe_comp_name}/{safe_filename}"
                                        
                                        success, result = upload_file_to_storage(img_file, "images", file_path)
                                        if success:
                                            image_urls.append(result)
                                except:
                                    pass
                            
                            data = {
                                "unit_name": unit_name,
                                "competition_date": comp['competition_date'],
                                "competition_name": comp['competition_name'],
                                "description": comp['description'],
                                "image_urls": json.dumps(image_urls),
                                "created_at": datetime.now().isoformat()
                            }
                            success, result = save_to_supabase("competitions", data)
                            if success:
                                success_count += 1
                                delete_pending_item("pending_competitions", comp['id'])
                        
                        if success_count == len(pending_comps):
                            st.success(f"✅ 成功提交{success_count}条技能竞赛记录！")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ 成功提交{success_count}条")
            
            st.markdown("---")
        
        with st.form(key="comp_form_new"):
            st.markdown("### ➕ 添加技能竞赛")
            
            col1, col2 = st.columns(2)
            with col1:
                comp_date = st.date_input("竞赛日期*")
            with col2:
                comp_name = st.text_input("竞赛名称*")
            
            comp_desc = st.text_area("竞赛简介*", height=100)
            
            comp_images = st.file_uploader(
                "上传竞赛图片",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="comp_images_new"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加到待提交", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并立即提交", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if comp_name and comp_desc:
                    image_data_list = []
                    if comp_images:
                        for img in comp_images:
                            image_data_list.append({
                                'name': img.name,
                                'type': img.type,
                                'data': file_to_base64(img)
                            })
                    
                    if submit_and_continue:
                        pending_data = {
                            "unit_name": unit_name,
                            "competition_date": str(comp_date),
                            "competition_name": comp_name,
                            "description": comp_desc,
                            "image_data": json.dumps(image_data_list) if image_data_list else None
                        }
                        success, result = save_pending_item("pending_competitions", pending_data)
                        if success:
                            st.success(f"✅ 已添加到待提交：{comp_name}")
                            st.info("💡 请点击上方【提交全部待提交内容】按钮完成提交")
                            st.rerun()
                        else:
                            st.error("❌ 保存失败")
                    
                    elif submit_final:
                        with st.spinner("正在上传数据..."):
                            image_urls = []
                            safe_unit_folder = get_unit_safe_name(unit_name)
                            
                            if comp_images:
                                for img_idx, img in enumerate(comp_images):
                                    safe_filename = generate_safe_filename(img.name, prefix=f"comp_{img_idx}")
                                    safe_comp_name = sanitize_path(comp_name[:30])
                                    file_path = f"{safe_unit_folder}/competition/{safe_comp_name}/{safe_filename}"
                                    
                                    success, result = upload_file_to_storage(img, "images", file_path)
                                    if success:
                                        image_urls.append(result)
                            
                            data = {
                                "unit_name": unit_name,
                                "competition_date": str(comp_date),
                                "competition_name": comp_name,
                                "description": comp_desc,
                                "image_urls": json.dumps(image_urls),
                                "created_at": datetime.now().isoformat()
                            }
                            success, result = save_to_supabase("competitions", data)
                            if success:
                                st.success(f"✅ 成功提交1条技能竞赛记录！")
                                st.rerun()
                else:
                    st.error("❌ 请填写所有必填项（标有*）")
    
    # ========== 获奖情况 ==========
    with tabs[4]:
        st.subheader("获奖情况登记")
        
        submitted_awards = load_activities("awards", unit_name)
        
        if submitted_awards:
            st.success(f"✅ 您已提交 {len(submitted_awards)} 条获奖记录")
            with st.expander("📋 查看已提交的获奖情况", expanded=False):
                for idx, award in enumerate(submitted_awards, 1):
                    st.markdown(f"### {idx}. {award['award_name']} ({award['award_date']})")
                    st.write(f"**颁奖单位：** {award.get('award_organization', '未填写')}")
                    
                    image_urls = json.loads(award.get('image_urls', '[]'))
                    if image_urls:
                        st.write(f"**图片：** {len(image_urls)}张")
                        cols = st.columns(min(len(image_urls), 3))
                        for img_idx, img_url in enumerate(image_urls):
                            with cols[img_idx % 3]:
                                try:
                                    st.image(img_url, use_container_width=True)
                                except:
                                    st.markdown(f"[🖼️ 查看图片]({img_url})")
                    
                    if st.button(f"🗑️ 删除此条记录", key=f"del_submitted_award_{award['id']}"):
                        success, _ = delete_from_supabase("awards", award['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
                        else:
                            st.error("删除失败，请重试")
                    st.markdown("---")
        
        pending_awards = load_pending_data("pending_awards", unit_name)
        
        if pending_awards:
            st.markdown("### 📝 待提交的获奖记录")
            st.warning(f"⏳ 您有 {len(pending_awards)} 条待提交的获奖记录")
            
            for idx, award in enumerate(pending_awards):
                with st.expander(f"⏳ {idx+1}. {award['award_name']} - {award['award_date']}", expanded=False):
                    st.write(f"**获奖日期：** {award['award_date']}")
                    st.write(f"**奖项名称：** {award['award_name']}")
                    st.write(f"**颁奖单位：** {award['award_organization']}")
                    
                    if award.get('image_data'):
                        try:
                            image_info = json.loads(award['image_data'])
                            if image_info:
                                st.write(f"**获奖图片：** {len(image_info)}张")
                                cols = st.columns(min(len(image_info), 3))
                                for img_idx, img_data in enumerate(image_info):
                                    with cols[img_idx % 3]:
                                        try:
                                            img_bytes = base64.b64decode(img_data['data'])
                                            st.image(img_bytes, caption=f"图片 {img_idx+1}", use_container_width=True)
                                        except:
                                            pass
                        except:
                            pass
                    
                    if st.button(f"🗑️ 删除此条", key=f"del_pending_award_{award['id']}"):
                        success, _ = delete_pending_item("pending_awards", award['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("💾 提交全部待提交内容", key="submit_all_pending_awards", type="primary", use_container_width=True):
                    with st.spinner("正在提交数据..."):
                        success_count = 0
                        safe_unit_folder = get_unit_safe_name(unit_name)
                        
                        for award in pending_awards:
                            image_urls = []
                            
                            if award.get('image_data'):
                                try:
                                    image_info = json.loads(award['image_data'])
                                    for img_idx, img_data in enumerate(image_info):
                                        img_file = base64_to_file(img_data['data'], img_data['name'], img_data['type'])
                                        safe_filename = generate_safe_filename(img_file.name, prefix=f"award_{img_idx}")
                                        safe_award_name = sanitize_path(award['award_name'][:30])
                                        file_path = f"{safe_unit_folder}/award/{safe_award_name}/{safe_filename}"
                                        
                                        success, result = upload_file_to_storage(img_file, "images", file_path)
                                        if success:
                                            image_urls.append(result)
                                except:
                                    pass
                            
                            data = {
                                "unit_name": unit_name,
                                "award_date": award['award_date'],
                                "award_name": award['award_name'],
                                "award_organization": award['award_organization'],
                                "image_urls": json.dumps(image_urls),
                                "created_at": datetime.now().isoformat()
                            }
                            success, result = save_to_supabase("awards", data)
                            if success:
                                success_count += 1
                                delete_pending_item("pending_awards", award['id'])
                        
                        if success_count == len(pending_awards):
                            st.success(f"✅ 成功提交{success_count}条获奖记录！")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ 成功提交{success_count}条")
            
            st.markdown("---")
        
        with st.form(key="award_form_new"):
            st.markdown("### ➕ 添加获奖记录")
            
            col1, col2 = st.columns(2)
            with col1:
                award_date = st.date_input("获奖日期*")
                award_name = st.text_input("奖项名称*")
            with col2:
                award_organization = st.text_input("颁奖单位*", placeholder="例如：揭阳市卫生健康局")
            
            award_images = st.file_uploader(
                "上传获奖图片",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="award_images_new"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加到待提交", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并立即提交", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if award_name and award_organization:
                    image_data_list = []
                    if award_images:
                        for img in award_images:
                            image_data_list.append({
                                'name': img.name,
                                'type': img.type,
                                'data': file_to_base64(img)
                            })
                    
                    if submit_and_continue:
                        pending_data = {
                            "unit_name": unit_name,
                            "award_date": str(award_date),
                            "award_name": award_name,
                            "award_organization": award_organization,
                            "image_data": json.dumps(image_data_list) if image_data_list else None
                        }
                        success, result = save_pending_item("pending_awards", pending_data)
                        if success:
                            st.success(f"✅ 已添加到待提交：{award_name}")
                            st.info("💡 请点击上方【提交全部待提交内容】按钮完成提交")
                            st.rerun()
                        else:
                            st.error("❌ 保存失败")
                    
                    elif submit_final:
                        with st.spinner("正在上传数据..."):
                            image_urls = []
                            safe_unit_folder = get_unit_safe_name(unit_name)
                            
                            if award_images:
                                for img_idx, img in enumerate(award_images):
                                    safe_filename = generate_safe_filename(img.name, prefix=f"award_{img_idx}")
                                    safe_award_name = sanitize_path(award_name[:30])
                                    file_path = f"{safe_unit_folder}/award/{safe_award_name}/{safe_filename}"
                                    
                                    success, result = upload_file_to_storage(img, "images", file_path)
                                    if success:
                                        image_urls.append(result)
                            
                            data = {
                                "unit_name": unit_name,
                                "award_date": str(award_date),
                                "award_name": award_name,
                                "award_organization": award_organization,
                                "image_urls": json.dumps(image_urls),
                                "created_at": datetime.now().isoformat()
                            }
                            success, result = save_to_supabase("awards", data)
                            if success:
                                st.success(f"✅ 成功提交1条获奖记录！")
                                st.rerun()
                else:
                    st.error("❌ 请填写所有必填项（奖项名称和颁奖单位）")
    
    # ========== 科研立项 ==========
    with tabs[5]:
        st.subheader("科研立项登记")
        
        submitted_projects = load_activities("research_projects", unit_name)
        
        if submitted_projects:
            st.success(f"✅ 您已提交 {len(submitted_projects)} 条科研立项")
            with st.expander("📋 查看已提交的科研立项", expanded=False):
                df_data = []
                for proj in submitted_projects:
                    df_data.append({
                        'ID': proj['id'],
                        '项目负责人': proj['project_leader'],
                        '项目名称': proj['project_name'],
                        '立项单位': proj['project_unit'],
                        '基金名称': proj['fund_name'],
                        '编号': proj['fund_number'],
                        '资助金额（万元）': proj['fund_amount'],
                        '立项时间': proj['project_date']
                    })
                df = pd.DataFrame(df_data)
                st.dataframe(df.drop('ID', axis=1), use_container_width=True, hide_index=True)
                
                for proj in submitted_projects:
                    col1, col2 = st.columns([8, 2])
                    with col1:
                        st.write(f"**{proj['project_name']}** - {proj['project_leader']}")
                    with col2:
                        if st.button(f"🗑️ 删除", key=f"del_submitted_proj_{proj['id']}"):
                            success, _ = delete_from_supabase("research_projects", proj['id'])
                            if success:
                                st.success("删除成功！")
                                st.rerun()
                            else:
                                st.error("删除失败，请重试")
        
        pending_projects = load_pending_data("pending_research_projects", unit_name)
        
        if pending_projects:
            st.markdown("### 📝 待提交的科研立项")
            st.warning(f"⏳ 您有 {len(pending_projects)} 条待提交的科研立项")
            
            df_data = []
            for proj in pending_projects:
                df_data.append({
                    'ID': proj['id'],
                    '项目负责人': proj['project_leader'],
                    '项目名称': proj['project_name'],
                    '立项单位': proj['project_unit'],
                    '基金名称': proj['fund_name'],
                    '编号': proj['fund_number'],
                    '资助金额（万元）': proj['fund_amount'],
                    '立项时间': proj['project_date']
                })
            df = pd.DataFrame(df_data)
            st.dataframe(df.drop('ID', axis=1), use_container_width=True, hide_index=True)
            
            for idx, proj in enumerate(pending_projects):
                col1, col2 = st.columns([8, 2])
                with col1:
                    st.write(f"{idx+1}. {proj['project_name']}")
                with col2:
                    if st.button(f"🗑️ 删除", key=f"del_pending_proj_{proj['id']}"):
                        success, _ = delete_pending_item("pending_research_projects", proj['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("💾 提交全部待提交内容", key="submit_all_pending_projects", type="primary", use_container_width=True):
                    with st.spinner("正在保存数据..."):
                        success_count = 0
                        for proj in pending_projects:
                            data = {
                                "unit_name": unit_name,
                                "project_leader": proj['project_leader'],
                                "project_name": proj['project_name'],
                                "project_unit": proj['project_unit'],
                                "fund_name": proj['fund_name'],
                                "fund_number": proj['fund_number'],
                                "fund_amount": proj['fund_amount'],
                                "project_date": proj['project_date'],
                                "created_at": datetime.now().isoformat()
                            }
                            success, result = save_to_supabase("research_projects", data)
                            if success:
                                success_count += 1
                                delete_pending_item("pending_research_projects", proj['id'])
                        
                        if success_count == len(pending_projects):
                            st.success(f"✅ 成功提交{success_count}条科研立项记录！")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ 成功提交{success_count}条")
            
            st.markdown("---")
        
        with st.form(key="project_form_new"):
            st.markdown("### ➕ 添加科研立项")
            st.info("⚠️ 除资助金额外，其他字段均为必填项")
            
            col1, col2 = st.columns(2)
            with col1:
                project_leader = st.text_input("项目负责人*")
                project_name = st.text_input("项目名称*")
                project_unit = st.text_input("立项单位*", value=unit_name)
            
            with col2:
                fund_name = st.text_input("基金名称*")
                fund_number = st.text_input("编号*")
                fund_amount = st.number_input("资助金额（万元）", min_value=0.0, step=0.1, value=0.0)
            
            project_date = st.date_input("立项时间*")
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加到待提交", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并立即提交", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if project_leader and project_name and project_unit and fund_name and fund_number:
                    if submit_and_continue:
                        pending_data = {
                            "unit_name": unit_name,
                            "project_leader": project_leader,
                            "project_name": project_name,
                            "project_unit": project_unit,
                            "fund_name": fund_name,
                            "fund_number": fund_number,
                            "fund_amount": fund_amount,
                            "project_date": str(project_date)
                        }
                        success, result = save_pending_item("pending_research_projects", pending_data)
                        if success:
                            st.success(f"✅ 已添加到待提交：{project_name}")
                            st.info("💡 请点击上方【提交全部待提交内容】按钮完成提交")
                            st.rerun()
                        else:
                            st.error("❌ 保存失败")
                    
                    elif submit_final:
                        with st.spinner("正在保存数据..."):
                            data = {
                                "unit_name": unit_name,
                                "project_leader": project_leader,
                                "project_name": project_name,
                                "project_unit": project_unit,
                                "fund_name": fund_name,
                                "fund_number": fund_number,
                                "fund_amount": fund_amount,
                                "project_date": str(project_date),
                                "created_at": datetime.now().isoformat()
                            }
                            success, result = save_to_supabase("research_projects", data)
                            if success:
                                st.success(f"✅ 成功提交1条科研立项记录！")
                                st.rerun()
                else:
                    st.error("❌ 请填写所有必填项（除资助金额外）")
    
    # ========== 论文发表 ==========
    with tabs[6]:
        st.subheader("论文发表登记")
        
        submitted_pubs = load_activities("publications", unit_name)
        
        if submitted_pubs:
            st.success(f"✅ 您已提交 {len(submitted_pubs)} 条论文发表")
            with st.expander("📋 查看已提交的论文发表", expanded=False):
                df_data = []
                for pub in submitted_pubs:
                    df_data.append({
                        'ID': pub['id'],
                        '类型': pub['publication_type'],
                        '题目': pub['title'],
                        '刊物名称': pub['journal'],
                        '作者': pub['author'],
                        '刊物等级': pub['level'],
                        '发表时间': pub['publication_date']
                    })
                df = pd.DataFrame(df_data)
                st.dataframe(df.drop('ID', axis=1), use_container_width=True, hide_index=True)
                
                for pub in submitted_pubs:
                    col1, col2 = st.columns([8, 2])
                    with col1:
                        st.write(f"**{pub['title']}** - {pub['author']}")
                    with col2:
                        if st.button(f"🗑️ 删除", key=f"del_submitted_pub_{pub['id']}"):
                            success, _ = delete_from_supabase("publications", pub['id'])
                            if success:
                                st.success("删除成功！")
                                st.rerun()
                            else:
                                st.error("删除失败，请重试")
        
        pending_pubs = load_pending_data("pending_publications", unit_name)
        
        if pending_pubs:
            st.markdown("### 📝 待提交的论文发表")
            st.warning(f"⏳ 您有 {len(pending_pubs)} 条待提交的论文发表")
            
            df_data = []
            for pub in pending_pubs:
                df_data.append({
                    'ID': pub['id'],
                    '类型': pub['publication_type'],
                    '题目': pub['title'],
                    '刊物名称': pub['journal'],
                    '作者': pub['author'],
                    '刊物等级': pub['level'],
                    '发表时间': pub['publication_date']
                })
            df = pd.DataFrame(df_data)
            st.dataframe(df.drop('ID', axis=1), use_container_width=True, hide_index=True)
            
            for idx, pub in enumerate(pending_pubs):
                col1, col2 = st.columns([8, 2])
                with col1:
                    st.write(f"{idx+1}. {pub['title']}")
                with col2:
                    if st.button(f"🗑️ 删除", key=f"del_pending_pub_{pub['id']}"):
                        success, _ = delete_pending_item("pending_publications", pub['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("💾 提交全部待提交内容", key="submit_all_pending_pubs", type="primary", use_container_width=True):
                    with st.spinner("正在保存数据..."):
                        success_count = 0
                        for pub in pending_pubs:
                            data = {
                                "unit_name": unit_name,
                                "publication_type": pub['publication_type'],
                                "title": pub['title'],
                                "journal": pub['journal'],
                                "cn_number": pub.get('cn_number', ''),
                                "department": pub.get('department', ''),
                                "issue": pub.get('issue', ''),
                                "pages": pub.get('pages', ''),
                                "author": pub['author'],
                                "level": pub['level'],
                                "publication_date": pub['publication_date'],
                                "created_at": datetime.now().isoformat()
                            }
                            success, result = save_to_supabase("publications", data)
                            if success:
                                success_count += 1
                                delete_pending_item("pending_publications", pub['id'])
                        
                        if success_count == len(pending_pubs):
                            st.success(f"✅ 成功提交{success_count}条论文发表记录！")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ 成功提交{success_count}条")
            
            st.markdown("---")
        
        with st.form(key="pub_form_new"):
            st.markdown("### ➕ 添加论文发表")
            
            pub_type = st.selectbox(
                "类型*",
                ["论文", "专著", "专利"]
            )
            
            col1, col2 = st.columns(2)
            with col1:
                pub_title = st.text_input("论文/专著/专利题目*")
                pub_journal = st.text_input("刊物/专著名称*")
                pub_cn = st.text_input("刊物CN号/出版社名称")
                pub_department = st.text_input("刊物主管部门")
            
            with col2:
                pub_issue = st.text_input("期刊、卷期")
                pub_pages = st.text_input("页码")
                pub_author = st.text_input("第一作者/通讯作者*")
                pub_level = st.selectbox(
                    "刊物等级*",
                    ["", "SCI", "中文核心期刊", "科技核心", "省级期刊", "其他"]
                )
            
            pub_date = st.date_input("发表时间*")
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加到待提交", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并立即提交", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if pub_title and pub_author and pub_journal and pub_level:
                    if submit_and_continue:
                        pending_data = {
                            "unit_name": unit_name,
                            "publication_type": pub_type,
                            "title": pub_title,
                            "journal": pub_journal,
                            "cn_number": pub_cn,
                            "department": pub_department,
                            "issue": pub_issue,
                            "pages": pub_pages,
                            "author": pub_author,
                            "level": pub_level,
                            "publication_date": str(pub_date)
                        }
                        success, result = save_pending_item("pending_publications", pending_data)
                        if success:
                            st.success(f"✅ 已添加到待提交：{pub_title}")
                            st.info("💡 请点击上方【提交全部待提交内容】按钮完成提交")
                            st.rerun()
                        else:
                            st.error("❌ 保存失败")
                    
                    elif submit_final:
                        with st.spinner("正在保存数据..."):
                            data = {
                                "unit_name": unit_name,
                                "publication_type": pub_type,
                                "title": pub_title,
                                "journal": pub_journal,
                                "cn_number": pub_cn,
                                "department": pub_department,
                                "issue": pub_issue,
                                "pages": pub_pages,
                                "author": pub_author,
                                "level": pub_level,
                                "publication_date": str(pub_date),
                                "created_at": datetime.now().isoformat()
                            }
                            success, result = save_to_supabase("publications", data)
                            if success:
                                st.success(f"✅ 成功提交1条论文发表记录！")
                                st.rerun()
                else:
                    st.error("❌ 请填写所有必填项（题目、作者、刊物名称、刊物等级）")
    
    # ========== 提交概览 ==========
    with tabs[7]:
        st.subheader("📊 提交概览")
        st.info("💡 这里显示当前已提交到数据库的数据统计")
        
        col1, col2, col3, col4 = st.columns(4)
        
        academic_count = len(get_from_supabase("academic_activities", unit_name))
        popular_count = len(get_from_supabase("popular_activities", unit_name))
        comp_count = len(get_from_supabase("competitions", unit_name))
        award_count = len(get_from_supabase("awards", unit_name))
        
        with col1:
            st.metric("学术活动", academic_count)
        with col2:
            st.metric("科普活动", popular_count)
        with col3:
            st.metric("技能竞赛", comp_count)
        with col4:
            st.metric("获奖情况", award_count)
        
        col1, col2, col3 = st.columns(3)
        
        project_count = len(get_from_supabase("research_projects", unit_name))
        pub_count = len(get_from_supabase("publications", unit_name))
        summary_docs = load_summary_documents(unit_name)
        summary_count = len(summary_docs)
        
        with col1:
            st.metric("科研立项", project_count)
        with col2:
            st.metric("论文发表", pub_count)
        with col3:
            st.metric("年度总结版本", summary_count)
        
        # 显示待提交统计
        st.markdown("---")
        st.subheader("⏳ 待提交数据统计")
        
        col1, col2, col3, col4 = st.columns(4)
        
        pending_academic_count = len(load_pending_data("pending_academic_activities", unit_name))
        pending_popular_count = len(load_pending_data("pending_popular_activities", unit_name))
        pending_comp_count = len(load_pending_data("pending_competitions", unit_name))
        pending_award_count = len(load_pending_data("pending_awards", unit_name))
        
        with col1:
            st.metric("待提交学术活动", pending_academic_count)
        with col2:
            st.metric("待提交科普活动", pending_popular_count)
        with col3:
            st.metric("待提交技能竞赛", pending_comp_count)
        with col4:
            st.metric("待提交获奖情况", pending_award_count)
        
        col1, col2 = st.columns(2)
        
        pending_project_count = len(load_pending_data("pending_research_projects", unit_name))
        pending_pub_count = len(load_pending_data("pending_publications", unit_name))
        
        with col1:
            st.metric("待提交科研立项", pending_project_count)
        with col2:
            st.metric("待提交论文发表", pending_pub_count)
        
        total_pending = pending_academic_count + pending_popular_count + pending_comp_count + pending_award_count + pending_project_count + pending_pub_count
        
        if total_pending > 0:
            st.warning(f"⚠️ 您有 {total_pending} 条数据待提交，请前往对应标签页完成提交")
        
        st.markdown("---")
        st.success("✅ 所有已提交数据已保存到云端数据库，管理员可实时查看")
        st.info("💡 您可以随时重新打开此页面查看和管理已提交的数据，待提交的数据会自动保存，即使刷新页面也不会丢失")

if __name__ == "__main__":
    main()
