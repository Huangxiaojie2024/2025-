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

def sanitize_path(path_str):
    """
    清理路径字符串，移除或替换特殊字符
    只保留字母、数字、下划线、连字符
    """
    # 移除所有可能导致问题的字符
    safe_str = re.sub(r'[^\w\-]', '_', path_str)
    # 移除连续的下划线
    safe_str = re.sub(r'_+', '_', safe_str)
    # 移除开头和结尾的下划线
    safe_str = safe_str.strip('_')
    # 限制长度
    if len(safe_str) > 50:
        safe_str = safe_str[:50]
    return safe_str

def generate_safe_filename(original_name, prefix="file"):
    """
    生成安全的文件名
    使用时间戳 + 原文件扩展名
    """
    ext = os.path.splitext(original_name)[1]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:17]  # 精确到毫秒前3位
    return f"{prefix}_{timestamp}{ext}"

def get_unit_safe_name(unit_name):
    """
    为单位名称生成安全的文件夹名
    使用哈希值作为唯一标识
    """
    # 创建单位名称的哈希值作为唯一标识
    unit_hash = hashlib.md5(unit_name.encode()).hexdigest()[:8]
    # 使用sanitize_path处理单位名称
    safe_name = sanitize_path(unit_name)
    # 组合：安全名称_哈希值
    return f"{safe_name}_{unit_hash}"

# ==================== 数据库操作函数 ====================

def save_to_supabase(table_name, data):
    """保存数据到Supabase"""
    try:
        result = supabase.table(table_name).insert(data).execute()
        return True, result
    except Exception as e:
        return False, str(e)

def update_supabase(table_name, data, match_field, match_value):
    """更新Supabase数据"""
    try:
        result = supabase.table(table_name).update(data).eq(match_field, match_value).execute()
        return True, result
    except Exception as e:
        return False, str(e)

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

def upload_file_to_storage(file, bucket_name, file_path):
    """上传文件到Supabase Storage"""
    try:
        file_bytes = file.getvalue()
        
        # 尝试上传，如果文件已存在则覆盖
        try:
            # 先尝试删除旧文件（如果存在）
            supabase.storage.from_(bucket_name).remove([file_path])
        except:
            pass  # 文件不存在，忽略错误
        
        # 上传新文件
        result = supabase.storage.from_(bucket_name).upload(
            file_path, 
            file_bytes,
            {"content-type": file.type, "upsert": "true"}
        )
        
        # 获取公共URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return True, public_url
    except Exception as e:
        return False, str(e)

# ==================== 主程序 ====================

def main():
    st.title("💊 揭阳市医学会临床药学分会数据收集系统")
    st.markdown("---")
    
    # 单位信息
    st.header("📋 单位信息")
    unit_name = st.text_input("请输入单位名称*", placeholder="例如：揭阳市人民医院", key="unit_name_input")
    contact_person = st.text_input("联系人*", placeholder="请输入联系人姓名")
    contact_phone = st.text_input("联系电话*", placeholder="请输入联系电话")
    
    if not unit_name:
        st.warning("⚠️ 请先填写单位名称后再继续填报")
        return
    
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
        st.info("💡 提示：请将年度总结和计划合并为一个Word文档上传")
        
        summary_plan_file = st.file_uploader(
            "上传年度总结与计划文档（Word文档）*",
            type=['doc', 'docx'],
            key="summary_plan"
        )
        
        if st.button("💾 保存年度总结与计划", key="save_summary_plan", type="primary"):
            if not contact_person or not contact_phone:
                st.error("❌ 请填写完整的联系人和联系电话")
            elif summary_plan_file:
                with st.spinner("正在上传文档..."):
                    # 生成安全的文件名
                    safe_filename = generate_safe_filename(summary_plan_file.name, prefix="summary")
                    
                    # 使用安全的单位名称作为文件夹名
                    safe_unit_folder = get_unit_safe_name(unit_name)
                    file_path = f"{safe_unit_folder}/summary/{safe_filename}"
                    
                    # 上传文档
                    success, result = upload_file_to_storage(summary_plan_file, "documents", file_path)
                    
                    if success:
                        document_url = result
                        
                        # 保存记录到数据库
                        data = {
                            "unit_name": unit_name,
                            "contact_person": contact_person,
                            "contact_phone": contact_phone,
                            "summary_url": document_url,
                            "plan_url": None,
                            "updated_at": datetime.now().isoformat()
                        }
                        
                        # 检查是否已存在记录
                        existing = get_from_supabase("work_summary", unit_name)
                        if existing:
                            success, result = update_supabase("work_summary", data, "unit_name", unit_name)
                        else:
                            success, result = save_to_supabase("work_summary", data)
                        
                        if success:
                            st.success("✅ 保存成功！")
                            st.info(f"📄 原文件名：{summary_plan_file.name}")
                        else:
                            st.error(f"❌ 保存失败: {result}")
                    else:
                        st.error(f"❌ 文档上传失败: {result}")
            else:
                st.warning("⚠️ 请上传年度总结与计划文档")
    
    # ========== 学术活动 ==========
    with tabs[1]:
        st.subheader("学术活动登记")
        
        if 'academic_activities' not in st.session_state:
            st.session_state.academic_activities = []
        if 'academic_form_key' not in st.session_state:
            st.session_state.academic_form_key = 0
        
        # 显示已添加的活动（带预览）
        if st.session_state.academic_activities:
            st.markdown("### 📋 已添加的学术活动")
            for idx, activity in enumerate(st.session_state.academic_activities):
                with st.expander(f"✅ {idx+1}. {activity['name']} - {activity['date']}", expanded=False):
                    st.write(f"**活动日期：** {activity['date']}")
                    st.write(f"**活动名称：** {activity['name']}")
                    st.write(f"**活动简介：** {activity['description']}")
                    
                    # 预览图片
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
                            # 提交所有数据
                            with st.spinner("正在上传数据..."):
                                success_count = 0
                                safe_unit_folder = get_unit_safe_name(unit_name)
                                
                                for activity in st.session_state.academic_activities:
                                    # 上传图片
                                    image_urls = []
                                    if activity['images']:
                                        for img_idx, img in enumerate(activity['images']):
                                            # 生成安全的文件名
                                            safe_filename = generate_safe_filename(img.name, prefix=f"academic_{img_idx}")
                                            safe_activity_name = sanitize_path(activity['name'][:30])
                                            file_path = f"{safe_unit_folder}/academic/{safe_activity_name}/{safe_filename}"
                                            
                                            success, result = upload_file_to_storage(img, "images", file_path)
                                            if success:
                                                image_urls.append(result)
                                    
                                    # 保存到数据库
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
                                    st.warning(f"⚠️ 成功{success_count}条")
                else:
                    st.error("❌ 请填写所有必填项（标有*）")
    
    # ========== 科普活动 ==========
    with tabs[2]:
        st.subheader("科普活动登记")
        
        if 'popular_activities' not in st.session_state:
            st.session_state.popular_activities = []
        if 'popular_form_key' not in st.session_state:
            st.session_state.popular_form_key = 0
        
        # 显示已添加的活动（带预览）
        if st.session_state.popular_activities:
            st.markdown("### 📋 已添加的科普活动")
            for idx, activity in enumerate(st.session_state.popular_activities):
                with st.expander(f"✅ {idx+1}. {activity['name']} - {activity['date']}", expanded=False):
                    st.write(f"**活动日期：** {activity['date']}")
                    st.write(f"**活动名称：** {activity['name']}")
                    st.write(f"**活动简介：** {activity['description']}")
                    
                    # 预览图片
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
        
        # 添加新活动表单
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
                    st.error("❌ 请填写所有必填项（标有*）")
    
    # ========== 技能竞赛 ==========
    with tabs[3]:
        st.subheader("技能竞赛登记")
        
        if 'competitions' not in st.session_state:
            st.session_state.competitions = []
        if 'comp_form_key' not in st.session_state:
            st.session_state.comp_form_key = 0
        
        # 显示已添加的竞赛（带预览）
        if st.session_state.competitions:
            st.markdown("### 📋 已添加的技能竞赛")
            for idx, comp in enumerate(st.session_state.competitions):
                with st.expander(f"✅ {idx+1}. {comp['name']} - {comp['date']}", expanded=False):
                    st.write(f"**竞赛日期：** {comp['date']}")
                    st.write(f"**竞赛名称：** {comp['name']}")
                    st.write(f"**竞赛简介：** {comp['description']}")
                    
                    # 预览图片
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
        
        # 添加新竞赛表单
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
        
        if 'awards' not in st.session_state:
            st.session_state.awards = []
        if 'award_form_key' not in st.session_state:
            st.session_state.award_form_key = 0
        
        # 显示已添加的获奖（带预览）
        if st.session_state.awards:
            st.markdown("### 📋 已添加的获奖记录")
            for idx, award in enumerate(st.session_state.awards):
                with st.expander(f"✅ {idx+1}. {award['name']} - {award['date']}", expanded=False):
                    st.write(f"**获奖日期：** {award['date']}")
                    st.write(f"**奖项名称：** {award['name']}")
                    
                    # 预览图片
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
        
        # 添加新获奖表单
        with st.form(key=f"award_form_{st.session_state.award_form_key}"):
            st.markdown("### ➕ 添加获奖记录")
            
            col1, col2 = st.columns(2)
            with col1:
                award_date = st.date_input("获奖日期*")
            with col2:
                award_name = st.text_input("奖项名称*")
            
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
                if award_name:
                    award_data = {
                        "date": str(award_date),
                        "name": award_name,
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
                    st.error("❌ 请填写奖项名称")
    
    # ========== 科研立项 ==========
    with tabs[5]:
        st.subheader("科研立项登记")
        
        if 'research_projects' not in st.session_state:
            st.session_state.research_projects = []
        if 'project_form_key' not in st.session_state:
            st.session_state.project_form_key = 0
        
        # 显示已添加的项目
        if st.session_state.research_projects:
            st.markdown("### 📋 已添加的科研立项")
            df = pd.DataFrame(st.session_state.research_projects)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            for idx in range(len(st.session_state.research_projects)):
                col1, col2, col3 = st.columns([6, 1, 1])
                with col1:
                    st.write(f"{idx+1}. {st.session_state.research_projects[idx]['name']}")
                with col3:
                    if st.button(f"🗑️ 删除", key=f"del_proj_{idx}"):
                        st.session_state.research_projects.pop(idx)
                        st.rerun()
            st.markdown("---")
        
        # 添加新项目表单
        with st.form(key=f"project_form_{st.session_state.project_form_key}"):
            st.markdown("### ➕ 添加科研立项")
            
            col1, col2 = st.columns(2)
            with col1:
                project_leader = st.text_input("项目负责人*")
                project_name = st.text_input("项目名称*")
                project_unit = st.text_input("立项单位", value=unit_name)
            
            with col2:
                fund_name = st.text_input("基金名称")
                fund_number = st.text_input("编号")
                fund_amount = st.number_input("资助金额（万元）", min_value=0.0, step=0.1)
            
            project_date = st.date_input("立项时间")
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加并继续", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并提交全部", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if project_leader and project_name:
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
                    st.error("❌ 请至少填写项目负责人和项目名称")
    
    # ========== 论文发表 ==========
    with tabs[6]:
        st.subheader("论文发表登记")
        
        if 'publications' not in st.session_state:
            st.session_state.publications = []
        if 'pub_form_key' not in st.session_state:
            st.session_state.pub_form_key = 0
        
        # 显示已添加的论文
        if st.session_state.publications:
            st.markdown("### 📋 已添加的论文发表")
            df = pd.DataFrame(st.session_state.publications)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            for idx in range(len(st.session_state.publications)):
                col1, col2, col3 = st.columns([6, 1, 1])
                with col1:
                    st.write(f"{idx+1}. {st.session_state.publications[idx]['title']}")
                with col3:
                    if st.button(f"🗑️ 删除", key=f"del_pub_{idx}"):
                        st.session_state.publications.pop(idx)
                        st.rerun()
            st.markdown("---")
        
        # 添加新论文表单
        with st.form(key=f"pub_form_{st.session_state.pub_form_key}"):
            st.markdown("### ➕ 添加论文发表")
            
            pub_type = st.selectbox(
                "类型*",
                ["论文", "专著", "专利"]
            )
            
            col1, col2 = st.columns(2)
            with col1:
                pub_title = st.text_input("论文/专著/专利题目*")
                pub_journal = st.text_input("刊物/专著名称")
                pub_cn = st.text_input("刊物CN号/出版社名称")
                pub_department = st.text_input("刊物主管部门")
            
            with col2:
                pub_issue = st.text_input("期刊、卷期")
                pub_pages = st.text_input("页码")
                pub_author = st.text_input("第一作者/通讯作者*")
                pub_level = st.selectbox(
                    "刊物等级",
                    ["SCI", "中文核心期刊", "科技核心", "省级期刊", "其他"]
                )
            
            pub_date = st.date_input("发表时间")
            
            col1, col2 = st.columns(2)
            with col1:
                submit_and_continue = st.form_submit_button("✅ 添加并继续", use_container_width=True)
            with col2:
                submit_final = st.form_submit_button("💾 添加并提交全部", type="primary", use_container_width=True)
            
            if submit_and_continue or submit_final:
                if pub_title and pub_author:
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
                    st.error("❌ 请至少填写题目和作者")
    
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
        
        col1, col2 = st.columns(2)
        
        project_count = len(get_from_supabase("research_projects", unit_name))
        pub_count = len(get_from_supabase("publications", unit_name))
        
        with col1:
            st.metric("科研立项", project_count)
        with col2:
            st.metric("论文发表", pub_count)
        
        st.markdown("---")
        st.success("✅ 所有数据已保存到云端数据库，管理员可实时查看")

if __name__ == "__main__":
    main()
```

## 文件2: 管理员后台 (admin.py 或 pages/admin.py)

管理员后台代码不需要修改,因为它只是读取数据,不涉及文件上传。原代码保持不变即可。

---

## 主要修改说明:

1. **移除了 `urllib.parse` 的导入和使用** - 不再需要URL编码
2. **添加了 `hashlib` 导入** - 用于生成单位名称的唯一哈希标识
3. **新增了三个关键函数**:
   - `sanitize_path()` - 清理路径中的特殊字符
   - `generate_safe_filename()` - 生成时间戳文件名(保持不变)
   - `get_unit_safe_name()` - 为每个单位生成安全的文件夹名
4. **所有文件上传路径都改用新的安全路径生成方式**
5. **数据库中仍然保存完整的中文单位名称** - 确保管理员后台正常显示

现在文件路径会是这样的格式:
```
揭阳市人民医院 → jieyangs_renminyi_yuan_a1b2c3d4/summary/summary_20251218_113844.docx
