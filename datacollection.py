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
    # 移除所有空格和横线
    phone = phone.replace(" ", "").replace("-", "")
    # 检查是否为11位数字
    return len(phone) == 11 and phone.isdigit()

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
        
        # 直接上传新文件（带时间戳，不会覆盖）
        result = supabase.storage.from_(bucket_name).upload(
            file_path, 
            file_bytes,
            {"content-type": file.type, "upsert": "false"}
        )
        
        # 获取公共URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return True, public_url
    except Exception as e:
        return False, str(e)

def delete_file_from_storage(bucket_name, file_path):
    """从Supabase Storage删除文件"""
    try:
        # 从URL中提取路径
        if file_path.startswith('http'):
            # 提取路径部分
            parts = file_path.split('/storage/v1/object/public/' + bucket_name + '/')
            if len(parts) > 1:
                file_path = parts[1]
        
        result = supabase.storage.from_(bucket_name).remove([file_path])
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
    
    # 添加备注说明
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
                            # 删除存储中的文件
                            file_success, _ = delete_file_from_storage("documents", doc['document_url'])
                            # 删除数据库记录
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
                        # 生成带时间戳的安全文件名（不会覆盖）
                        safe_filename = generate_safe_filename(summary_plan_file.name, prefix="summary")
                        safe_unit_folder = get_unit_safe_name(unit_name)
                        file_path = f"{safe_unit_folder}/summary/{safe_filename}"
                        
                        st.info(f"📁 上传路径: {file_path}")
                        
                        # 上传文档
                        success, result = upload_file_to_storage(summary_plan_file, "documents", file_path)
                        
                        if success:
                            document_url = result
                            
                            # 保存文档记录到summary_documents表
                            doc_data = {
                                "unit_name": unit_name,
                                "document_url": document_url,
                                "original_filename": summary_plan_file.name,
                                "uploaded_at": datetime.now().isoformat()
                            }
                            doc_success, doc_result = save_to_supabase("summary_documents", doc_data)
                            
                            # 更新work_summary表的联系信息和最新文档URL
                            summary_update_data = {
                                "unit_name": unit_name,
                                "contact_person": contact_person,
                                "contact_phone": contact_phone,
                                "summary_url": document_url,  # 保存最新的文档URL
                                "updated_at": datetime.now().isoformat()
                            }
                            
                            # 检查是否已存在记录
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
                    
                    # 显示图片
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
                    
                    # 删除按钮
                    if st.button(f"🗑️ 删除此条记录", key=f"del_submitted_academic_{activity['id']}"):
                        success, _ = delete_from_supabase("academic_activities", activity['id'])
                        if success:
                            st.success("删除成功！")
                            st.rerun()
                        else:
                            st.error("删除失败，请重试")
                    st.markdown("---")
        
        # 待提交列表
        if 'academic_activities' not in st.session_state:
            st.session_state.academic_activities = []
        if 'academic_form_key' not in st.session_state:
            st.session_state.academic_form_key = 0
        
        # 显示待提交的活动
        if st.session_state.academic_activities:
            st.markdown("### 📝 待提交的学术活动")
            for idx, activity in enumerate(st.session_state.academic_activities):
                with st.expander(f"⏳ {idx+1}. {activity['name']} - {activity['date']}", expanded=False):
                    st.write(f"**活动日期：** {activity['date']}")
                    st.write(f"**活动名称：** {activity['name']}")
                    st.write(f"**活动简介：** {activity['description']}")
                    
                    if activity['images']:
                        st.write(f"**活动图片：** {len(activity['images'])}张")
                        cols = st.columns(min(len(activity['images']), 3))
                        for img_idx, img in enumerate(activity['images']):
                            with cols[img_idx % 3]:
                                st.image(img, caption=f"图片 {img_idx+1}", use_container_width=True)
                    
                    if st.button(f"🗑️ 删除此条", key=f"del_academic_{idx}"):
                        st.session_state.academic_activities.pop(idx)
                        st.rerun()
            st.markdown("---")
        
        # 添加新活动表单
        with st.form(key=f"academic_form_{st.session_state.academic_form_key}"):
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
                accept_multiple_files=True
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加并继续", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并提交全部", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if activity_name and activity_desc:
                    if activity_images and len(activity_images) > 3:
                        st.error("❌ 最多只能上传3张图片")
                    else:
                        activity_data = {
                            "date": str(activity_date),
                            "name": activity_name,
                            "description": activity_desc,
                            "images": activity_images if activity_images else [],
                            "image_count": len(activity_images) if activity_images else 0
                        }
                        st.session_state.academic_activities.append(activity_data)
                        
                        if submit_and_continue:
                            st.session_state.academic_form_key += 1
                            st.success(f"✅ 已添加：{activity_name}，请继续添加下一条")
                            st.rerun()
                        elif submit_final:
                            with st.spinner("正在上传数据..."):
                                success_count = 0
                                safe_unit_folder = get_unit_safe_name(unit_name)
                                
                                for activity in st.session_state.academic_activities:
                                    image_urls = []
                                    if activity['images']:
                                        for img_idx, img in enumerate(activity['images']):
                                            safe_filename = generate_safe_filename(img.name, prefix=f"academic_{img_idx}")
                                            safe_activity_name = sanitize_path(activity['name'][:30])
                                            file_path = f"{safe_unit_folder}/academic/{safe_activity_name}/{safe_filename}"
                                            
                                            success, result = upload_file_to_storage(img, "images", file_path)
                                            if success:
                                                image_urls.append(result)
                                    
                                    data = {
                                        "unit_name": unit_name,
                                        "activity_date": activity['date'],
                                        "activity_name": activity['name'],
                                        "description": activity['description'],
                                        "image_urls": json.dumps(image_urls),
                                        "created_at": datetime.now().isoformat()
                                    }
                                    success, result = save_to_supabase("academic_activities", data)
                                    if success:
                                        success_count += 1
                                
                                if success_count == len(st.session_state.academic_activities):
                                    st.success(f"✅ 成功提交{success_count}条学术活动记录！")
                                    st.session_state.academic_activities = []
                                    st.session_state.academic_form_key = 0
                                    st.rerun()
                                else:
                                    st.warning(f"⚠️ 成功提交{success_count}条")
                else:
                    st.error("❌ 请填写所有必填项（标有*）")
    
    # ========== 科普活动 ==========
    with tabs[2]:
        st.subheader("科普活动登记")
        
        # 加载已提交的数据
        submitted_popular = load_activities("popular_activities", unit_name)
        
        # 显示已提交的活动
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
        
        if 'popular_activities' not in st.session_state:
            st.session_state.popular_activities = []
        if 'popular_form_key' not in st.session_state:
            st.session_state.popular_form_key = 0
        
        if st.session_state.popular_activities:
            st.markdown("### 📝 待提交的科普活动")
            for idx, activity in enumerate(st.session_state.popular_activities):
                with st.expander(f"⏳ {idx+1}. {activity['name']} - {activity['date']}", expanded=False):
                    st.write(f"**活动日期：** {activity['date']}")
                    st.write(f"**活动名称：** {activity['name']}")
                    st.write(f"**活动简介：** {activity['description']}")
                    
                    if activity['images']:
                        st.write(f"**活动图片：** {len(activity['images'])}张")
                        cols = st.columns(min(len(activity['images']), 3))
                        for img_idx, img in enumerate(activity['images']):
                            with cols[img_idx % 3]:
                                st.image(img, caption=f"图片 {img_idx+1}", use_container_width=True)
                    
                    if st.button(f"🗑️ 删除此条", key=f"del_pop_{idx}"):
                        st.session_state.popular_activities.pop(idx)
                        st.rerun()
            st.markdown("---")
        
        with st.form(key=f"popular_form_{st.session_state.popular_form_key}"):
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
                accept_multiple_files=True
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加并继续", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并提交全部", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if pop_name and pop_desc:
                    if pop_images and len(pop_images) > 3:
                        st.error("❌ 最多只能上传3张图片")
                    else:
                        activity_data = {
                            "date": str(pop_date),
                            "name": pop_name,
                            "description": pop_desc,
                            "images": pop_images if pop_images else [],
                            "image_count": len(pop_images) if pop_images else 0
                        }
                        st.session_state.popular_activities.append(activity_data)
                        
                        if submit_and_continue:
                            st.session_state.popular_form_key += 1
                            st.success(f"✅ 已添加：{pop_name}，请继续添加下一条")
                            st.rerun()
                        elif submit_final:
                            with st.spinner("正在上传数据..."):
                                success_count = 0
                                safe_unit_folder = get_unit_safe_name(unit_name)
                                
                                for activity in st.session_state.popular_activities:
                                    image_urls = []
                                    if activity['images']:
                                        for img_idx, img in enumerate(activity['images']):
                                            safe_filename = generate_safe_filename(img.name, prefix=f"popular_{img_idx}")
                                            safe_activity_name = sanitize_path(activity['name'][:30])
                                            file_path = f"{safe_unit_folder}/popular/{safe_activity_name}/{safe_filename}"
                                            
                                            success, result = upload_file_to_storage(img, "images", file_path)
                                            if success:
                                                image_urls.append(result)
                                    
                                    data = {
                                        "unit_name": unit_name,
                                        "activity_date": activity['date'],
                                        "activity_name": activity['name'],
                                        "description": activity['description'],
                                        "image_urls": json.dumps(image_urls),
                                        "created_at": datetime.now().isoformat()
                                    }
                                    success, result = save_to_supabase("popular_activities", data)
                                    if success:
                                        success_count += 1
                                
                                if success_count == len(st.session_state.popular_activities):
                                    st.success(f"✅ 成功提交{success_count}条科普活动记录！")
                                    st.session_state.popular_activities = []
                                    st.session_state.popular_form_key = 0
                                    st.rerun()
                                else:
                                    st.warning(f"⚠️ 成功提交{success_count}条")
                else:
                    st.error("❌ 请填写所有必填项（标有*）")
    
    # ========== 技能竞赛 ==========
    with tabs[3]:
        st.subheader("技能竞赛登记")
        
        # 加载已提交的数据
        submitted_comps = load_activities("competitions", unit_name)
        
        # 显示已提交的竞赛
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
        
        if 'competitions' not in st.session_state:
            st.session_state.competitions = []
        if 'comp_form_key' not in st.session_state:
            st.session_state.comp_form_key = 0
        
        if st.session_state.competitions:
            st.markdown("### 📝 待提交的技能竞赛")
            for idx, comp in enumerate(st.session_state.competitions):
                with st.expander(f"⏳ {idx+1}. {comp['name']} - {comp['date']}", expanded=False):
                    st.write(f"**竞赛日期：** {comp['date']}")
                    st.write(f"**竞赛名称：** {comp['name']}")
                    st.write(f"**竞赛简介：** {comp['description']}")
                    
                    if comp['images']:
                        st.write(f"**竞赛图片：** {len(comp['images'])}张")
                        cols = st.columns(min(len(comp['images']), 3))
                        for img_idx, img in enumerate(comp['images']):
                            with cols[img_idx % 3]:
                                st.image(img, caption=f"图片 {img_idx+1}", use_container_width=True)
                    
                    if st.button(f"🗑️ 删除此条", key=f"del_comp_{idx}"):
                        st.session_state.competitions.pop(idx)
                        st.rerun()
            st.markdown("---")
        
        with st.form(key=f"comp_form_{st.session_state.comp_form_key}"):
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
                accept_multiple_files=True
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加并继续", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并提交全部", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if comp_name and comp_desc:
                    comp_data = {
                        "date": str(comp_date),
                        "name": comp_name,
                        "description": comp_desc,
                        "images": comp_images if comp_images else [],
                        "image_count": len(comp_images) if comp_images else 0
                    }
                    st.session_state.competitions.append(comp_data)
                    
                    if submit_and_continue:
                        st.session_state.comp_form_key += 1
                        st.success(f"✅ 已添加：{comp_name}，请继续添加下一条")
                        st.rerun()
                    elif submit_final:
                        with st.spinner("正在上传数据..."):
                            success_count = 0
                            safe_unit_folder = get_unit_safe_name(unit_name)
                            
                            for comp in st.session_state.competitions:
                                image_urls = []
                                if comp['images']:
                                    for img_idx, img in enumerate(comp['images']):
                                        safe_filename = generate_safe_filename(img.name, prefix=f"comp_{img_idx}")
                                        safe_comp_name = sanitize_path(comp['name'][:30])
                                        file_path = f"{safe_unit_folder}/competition/{safe_comp_name}/{safe_filename}"
                                        
                                        success, result = upload_file_to_storage(img, "images", file_path)
                                        if success:
                                            image_urls.append(result)
                                
                                data = {
                                    "unit_name": unit_name,
                                    "competition_date": comp['date'],
                                    "competition_name": comp['name'],
                                    "description": comp['description'],
                                    "image_urls": json.dumps(image_urls),
                                    "created_at": datetime.now().isoformat()
                                }
                                success, result = save_to_supabase("competitions", data)
                                if success:
                                    success_count += 1
                            
                            if success_count == len(st.session_state.competitions):
                                st.success(f"✅ 成功提交{success_count}条技能竞赛记录！")
                                st.session_state.competitions = []
                                st.session_state.comp_form_key = 0
                                st.rerun()
                else:
                    st.error("❌ 请填写所有必填项（标有*）")
    
    # ========== 获奖情况 ==========
    with tabs[4]:
        st.subheader("获奖情况登记")
        
        # 加载已提交的数据
        submitted_awards = load_activities("awards", unit_name)
        
        # 显示已提交的获奖
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
        
        if 'awards' not in st.session_state:
            st.session_state.awards = []
        if 'award_form_key' not in st.session_state:
            st.session_state.award_form_key = 0
        
        if st.session_state.awards:
            st.markdown("### 📝 待提交的获奖记录")
            for idx, award in enumerate(st.session_state.awards):
                with st.expander(f"⏳ {idx+1}. {award['name']} - {award['date']}", expanded=False):
                    st.write(f"**获奖日期：** {award['date']}")
                    st.write(f"**奖项名称：** {award['name']}")
                    st.write(f"**颁奖单位：** {award['organization']}")
                    
                    if award['images']:
                        st.write(f"**获奖图片：** {len(award['images'])}张")
                        cols = st.columns(min(len(award['images']), 3))
                        for img_idx, img in enumerate(award['images']):
                            with cols[img_idx % 3]:
                                st.image(img, caption=f"图片 {img_idx+1}", use_container_width=True)
                    
                    if st.button(f"🗑️ 删除此条", key=f"del_award_{idx}"):
                        st.session_state.awards.pop(idx)
                        st.rerun()
            st.markdown("---")
        
        with st.form(key=f"award_form_{st.session_state.award_form_key}"):
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
                accept_multiple_files=True
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加并继续", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并提交全部", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if award_name and award_organization:
                    award_data = {
                        "date": str(award_date),
                        "name": award_name,
                        "organization": award_organization,
                        "images": award_images if award_images else [],
                        "image_count": len(award_images) if award_images else 0
                    }
                    st.session_state.awards.append(award_data)
                    
                    if submit_and_continue:
                        st.session_state.award_form_key += 1
                        st.success(f"✅ 已添加：{award_name}，请继续添加下一条")
                        st.rerun()
                    elif submit_final:
                        with st.spinner("正在上传数据..."):
                            success_count = 0
                            safe_unit_folder = get_unit_safe_name(unit_name)
                            
                            for award in st.session_state.awards:
                                image_urls = []
                                if award['images']:
                                    for img_idx, img in enumerate(award['images']):
                                        safe_filename = generate_safe_filename(img.name, prefix=f"award_{img_idx}")
                                        safe_award_name = sanitize_path(award['name'][:30])
                                        file_path = f"{safe_unit_folder}/award/{safe_award_name}/{safe_filename}"
                                        
                                        success, result = upload_file_to_storage(img, "images", file_path)
                                        if success:
                                            image_urls.append(result)
                                
                                data = {
                                    "unit_name": unit_name,
                                    "award_date": award['date'],
                                    "award_name": award['name'],
                                    "award_organization": award['organization'],
                                    "image_urls": json.dumps(image_urls),
                                    "created_at": datetime.now().isoformat()
                                }
                                success, result = save_to_supabase("awards", data)
                                if success:
                                    success_count += 1
                            
                            if success_count == len(st.session_state.awards):
                                st.success(f"✅ 成功提交{success_count}条获奖记录！")
                                st.session_state.awards = []
                                st.session_state.award_form_key = 0
                                st.rerun()
                else:
                    st.error("❌ 请填写所有必填项（奖项名称和颁奖单位）")
    
    # ========== 科研立项 ==========
    with tabs[5]:
        st.subheader("科研立项登记")
        
        # 加载已提交的数据
        submitted_projects = load_activities("research_projects", unit_name)
        
        # 显示已提交的项目
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
                
                # 删除按钮
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
        
        if 'research_projects' not in st.session_state:
            st.session_state.research_projects = []
        if 'project_form_key' not in st.session_state:
            st.session_state.project_form_key = 0
        
        if st.session_state.research_projects:
            st.markdown("### 📝 待提交的科研立项")
            df = pd.DataFrame(st.session_state.research_projects)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            for idx in range(len(st.session_state.research_projects)):
                col1, col2 = st.columns([8, 2])
                with col1:
                    st.write(f"{idx+1}. {st.session_state.research_projects[idx]['name']}")
                with col2:
                    if st.button(f"🗑️ 删除", key=f"del_proj_{idx}"):
                        st.session_state.research_projects.pop(idx)
                        st.rerun()
            st.markdown("---")
        
        with st.form(key=f"project_form_{st.session_state.project_form_key}"):
            st.markdown("### ➕ 添加科研立项")
            st.info("⚠️ 所有字段均为必填项")
            
            col1, col2 = st.columns(2)
            with col1:
                project_leader = st.text_input("项目负责人*")
                project_name = st.text_input("项目名称*")
                project_unit = st.text_input("立项单位*", value=unit_name)
            
            with col2:
                fund_name = st.text_input("基金名称*")
                fund_number = st.text_input("编号*")
                fund_amount = st.number_input("资助金额（万元）*", min_value=0.0, step=0.1)
            
            project_date = st.date_input("立项时间*")
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加并继续", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并提交全部", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                # 验证所有必填字段
                if (project_leader and project_name and project_unit and 
                    fund_name and fund_number and fund_amount > 0):
                    project_data = {
                        "leader": project_leader,
                        "name": project_name,
                        "unit": project_unit,
                        "fund_name": fund_name,
                        "fund_number": fund_number,
                        "fund_amount": fund_amount,
                        "date": str(project_date)
                    }
                    st.session_state.research_projects.append(project_data)
                    
                    if submit_and_continue:
                        st.session_state.project_form_key += 1
                        st.success(f"✅ 已添加：{project_name}，请继续添加下一条")
                        st.rerun()
                    elif submit_final:
                        with st.spinner("正在保存数据..."):
                            success_count = 0
                            for proj in st.session_state.research_projects:
                                data = {
                                    "unit_name": unit_name,
                                    "project_leader": proj['leader'],
                                    "project_name": proj['name'],
                                    "project_unit": proj['unit'],
                                    "fund_name": proj['fund_name'],
                                    "fund_number": proj['fund_number'],
                                    "fund_amount": proj['fund_amount'],
                                    "project_date": proj['date'],
                                    "created_at": datetime.now().isoformat()
                                }
                                success, result = save_to_supabase("research_projects", data)
                                if success:
                                    success_count += 1
                            
                            if success_count == len(st.session_state.research_projects):
                                st.success(f"✅ 成功提交{success_count}条科研立项记录！")
                                st.session_state.research_projects = []
                                st.session_state.project_form_key = 0
                                st.rerun()
                else:
                    st.error("❌ 请填写所有必填项（所有字段都是必填的）")
    
    # ========== 论文发表 ==========
    with tabs[6]:
        st.subheader("论文发表登记")
        
        # 加载已提交的数据
        submitted_pubs = load_activities("publications", unit_name)
        
        # 显示已提交的论文
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
                
                # 删除按钮
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
        
        if 'publications' not in st.session_state:
            st.session_state.publications = []
        if 'pub_form_key' not in st.session_state:
            st.session_state.pub_form_key = 0
        
        if st.session_state.publications:
            st.markdown("### 📝 待提交的论文发表")
            df = pd.DataFrame(st.session_state.publications)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            for idx in range(len(st.session_state.publications)):
                col1, col2 = st.columns([8, 2])
                with col1:
                    st.write(f"{idx+1}. {st.session_state.publications[idx]['title']}")
                with col2:
                    if st.button(f"🗑️ 删除", key=f"del_pub_{idx}"):
                        st.session_state.publications.pop(idx)
                        st.rerun()
            st.markdown("---")
        
        with st.form(key=f"pub_form_{st.session_state.pub_form_key}"):
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
                submit_and_continue = st.form_submit_button("✅ 添加并继续", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并提交全部", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                # 验证必填字段
                if pub_title and pub_author and pub_journal and pub_level:
                    pub_data = {
                        "type": pub_type,
                        "title": pub_title,
                        "journal": pub_journal,
                        "cn_number": pub_cn,
                        "department": pub_department,
                        "issue": pub_issue,
                        "pages": pub_pages,
                        "author": pub_author,
                        "level": pub_level,
                        "date": str(pub_date)
                    }
                    st.session_state.publications.append(pub_data)
                    
                    if submit_and_continue:
                        st.session_state.pub_form_key += 1
                        st.success(f"✅ 已添加：{pub_title}，请继续添加下一条")
                        st.rerun()
                    elif submit_final:
                        with st.spinner("正在保存数据..."):
                            success_count = 0
                            for pub in st.session_state.publications:
                                data = {
                                    "unit_name": unit_name,
                                    "publication_type": pub['type'],
                                    "title": pub['title'],
                                    "journal": pub['journal'],
                                    "cn_number": pub['cn_number'],
                                    "department": pub['department'],
                                    "issue": pub['issue'],
                                    "pages": pub['pages'],
                                    "author": pub['author'],
                                    "level": pub['level'],
                                    "publication_date": pub['date'],
                                    "created_at": datetime.now().isoformat()
                                }
                                success, result = save_to_supabase("publications", data)
                                if success:
                                    success_count += 1
                            
                            if success_count == len(st.session_state.publications):
                                st.success(f"✅ 成功提交{success_count}条论文发表记录！")
                                st.session_state.publications = []
                                st.session_state.pub_form_key = 0
                                st.rerun()
                else:
                    st.error("❌ 请填写所有必填项（题目、作者、刊物名称、刊物等级）")
    
    # ========== 提交概览 ==========
    with tabs[7]:
        st.subheader("📊 提交概览")
        st.info("💡 这里显示当前已提交到数据库的数据统计")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # 统计各类数据
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
        
        st.markdown("---")
        st.success("✅ 所有数据已保存到云端数据库，管理员可实时查看")
        st.info("💡 您可以随时重新打开此页面查看和管理已提交的数据")

if __name__ == "__main__":
    main()
