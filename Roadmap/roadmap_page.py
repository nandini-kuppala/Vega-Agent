
import streamlit as st
from backend.database import get_profile, get_user_details
from Roadmap.roadmap import generate_learning_roadmap
from backend.database import save_roadmap, get_user_roadmaps, get_roadmap

def display_roadmap_page():
    """Display the learning roadmap page with personalized user details"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
        
    # Get user details from database
    user_result = get_user_details(st.session_state['user_id'])
    
    if user_result["status"] == "error":
        st.error(f"Error retrieving user details: {user_result['message']}")
        user_data = {"name": "User"}  # Fallback
    else:
        user_data = user_result["user"]
        
    # Use the user's name in the welcome message
    st.markdown(
        f"""
        <h1 style="color: #935073; text-align: center; font-size: 36px; font-weight: bold;">
            Hello, {user_data.get('name', 'there')}! Your Learning Roadmap Awaits! <span style="font-size: 40px;">🚀</span>
        </h1>
        <p style="text-align: center; font-size: 18px; color: #555;">
            Ready to take your career to the next level? With our tailor-made roadmap, 
            you'll get a clear path forward, personalized just for you based on your skills, goals, and experience. 
            Let's start crafting the future you've always wanted! 
        </p>
        
        """, unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Show user location if available
    if user_data.get('city'):
        st.markdown(f"<p style='text-align: center; font-style: italic;'>Location: {user_data.get('city')}</p>", unsafe_allow_html=True)
    
    # Try to get user profile information
    try:
        # Use direct database function to get profile
        result = get_profile(st.session_state['user_id'])
        
        if result["status"] == "success":
            profile_data = result["profile"]
            
            # Profile Summary Section
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"### 📋 Your Profile Summary")
                st.write(f"🎓 **Education**: {profile_data.get('education', 'Not specified')}")
                st.write(f"💼 **Experience**: {profile_data.get('experience_years', 0)} years")
                
                # Display skills as tags
                if profile_data.get('skills'):
                    st.write("🔧 **Current Skills**:")
                    skill_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
                    for skill in profile_data.get('skills', []):
                        skill_html += f"<span style='background-color: #f0f0f0; padding: 5px 10px; border-radius: 20px; font-size: 14px;'>{skill}</span>"
                    skill_html += "</div>"
                    st.markdown(skill_html, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"### 🎯 Career Goals")
                if 'job_preferences' in profile_data and profile_data['job_preferences']:
                    st.write(f"🎯 **Short-term Goal**: {profile_data['job_preferences'].get('short_term_goal', 'Not specified')}")
                    st.write(f"🚀 **Long-term Goal**: {profile_data['job_preferences'].get('long_term_goal', 'Not specified')}")
                    
                    # Display preferred roles
                    if 'roles' in profile_data['job_preferences']:
                        st.write("👔 **Preferred Roles**:")
                        roles_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
                        for role in profile_data['job_preferences']['roles']:
                            roles_html += f"<span style='background-color: #e6f3ff; padding: 5px 10px; border-radius: 20px; font-size: 14px;'>{role}</span>"
                        roles_html += "</div>"
                        st.markdown(roles_html, unsafe_allow_html=True)
                else:
                    st.info("Please complete your profile to view career goals")
                    
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # Learning goal input section
            st.markdown("### 📚 What's your learning goal?")
            
            # Default learning goal based on profile
            default_goal = profile_data.get('job_preferences', {}).get('short_term_goal', "")
            
            # Add some predefined learning goals to choose from
            goal_options = [
                "I want to become a Machine Learning Engineer",
                "I want to specialize in Natural Language Processing",
                "I want to become a Full Stack Developer",
                "I want to learn Data Science and Analytics",
                "I want to become a DevOps Engineer",
                "Custom Goal"
            ]
            
            # Goal selection dropdown
            selected_goal = st.selectbox("Select a learning goal", options=goal_options)
            
            if selected_goal == "Custom Goal":
                custom_goal = st.text_area("Enter your custom learning goal", 
                                          value=default_goal, 
                                          height=100, 
                                          placeholder="E.g., I want to become a proficient AI engineer...")
                learning_goal = custom_goal
            else:
                learning_goal = selected_goal
            
            # Format the user profile data for the roadmap generator
            user_profile_text = f"""
            **Name**: {user_data.get('name', 'User')}
            **Email**: {user_data.get('email', 'Not specified')}
            **Location**: {user_data.get('city', 'Not specified')}
            **Education**: {profile_data.get('education', 'Not specified')}
            
            **Skills**:
            {', '.join(profile_data.get('skills', ['None specified']))}
            
            **Experience**: {profile_data.get('experience_years', 0)} years
            """
            
            if profile_data.get('last_job'):
                user_profile_text += f"""
                **Last Job**: {profile_data['last_job'].get('title', 'Not specified')} at {profile_data['last_job'].get('company', 'Not specified')}
                """
            
            # Generate roadmap button
            if st.button("🔮 Generate Learning Roadmap", type="primary"):
                if learning_goal:
                    with st.spinner(f"Generating your personalized learning roadmap, {user_data.get('name').split()[0]}... This may take a few minutes."):
                        try:
                            # Call the CrewAI function to generate the roadmap
                            roadmap = generate_learning_roadmap(user_profile_text, learning_goal)
                            
                            # Save the roadmap to database
                            save_result = save_roadmap(st.session_state['user_id'], learning_goal, roadmap)
                            if save_result["status"] == "success":
                                st.success("Roadmap saved successfully!")
                            
                            # Store the roadmap in session state
                            st.session_state['current_roadmap'] = roadmap
                            st.session_state['current_roadmap_goal'] = learning_goal
                            
                            # Display the roadmap
                            st.markdown("## 🗺️ Your Personalized Learning Roadmap")
                            
                            st.markdown(roadmap)
                            
                            # Add a download button for the markdown file
                            st.download_button(
                                label=f"📥 Download {user_data.get('name').split()[0]}'s Roadmap",
                                data=roadmap,
                                file_name=f"{user_data.get('name').lower().replace(' ', '_')}_learning_roadmap.md",
                                mime="text/markdown"
                            )
                            
                        except Exception as e:
                            st.error(f"Error generating roadmap: {str(e)}")
                else:
                    st.warning("Please enter a learning goal first")

            # Display previously generated roadmap if it exists
            if 'current_roadmap' in st.session_state and not st.button:
                st.markdown("## 🗺️ Your Personalized Learning Roadmap")
                
                # Create tabs for viewing and raw formats
                tab1, tab2 = st.tabs(["Rendered View", "Raw Markdown"])
                
                with tab1:
                    # Render the markdown properly
                    st.markdown(st.session_state['current_roadmap'])
                
                with tab2:
                    # Show raw markdown with a monospace font
                    st.code(st.session_state['current_roadmap'], language="markdown")
                
                # Add a download button for the markdown file with personalized filename
                st.download_button(
                    label=f"📥 Download {user_data.get('name').split()[0]}'s Roadmap", 
                    data=st.session_state['current_roadmap'],
                    file_name=f"{user_data.get('name').lower().replace(' ', '_')}_learning_roadmap.md",
                    mime="text/markdown"
                )

            # Add spacing and previous roadmaps section
            st.markdown("<br><br><hr><br>", unsafe_allow_html=True)

            # Previous Roadmaps Section
            st.markdown("### 📚 Your Previous Learning Roadmaps")

            # Get user's previous roadmaps
            roadmaps_result = get_user_roadmaps(st.session_state['user_id'])

            if roadmaps_result["status"] == "success" and roadmaps_result["roadmaps"]:
                roadmaps = roadmaps_result["roadmaps"]
                
                # Create columns for roadmap buttons
                cols_per_row = 3
                for i in range(0, len(roadmaps), cols_per_row):
                    row_roadmaps = roadmaps[i:i + cols_per_row]
                    cols = st.columns(len(row_roadmaps))
                    
                    for j, roadmap in enumerate(row_roadmaps):
                        with cols[j]:
                            if st.button(
                                roadmap["display_name"], 
                                key=f"roadmap_{roadmap['_id']}",
                                help=f"Created: {roadmap['created_at'].strftime('%Y-%m-%d %H:%M')}"
                            ):
                                # Fetch and display the selected roadmap
                                roadmap_detail = get_roadmap(roadmap["_id"])
                                if roadmap_detail["status"] == "success":
                                    selected_roadmap = roadmap_detail["roadmap"]
                                    st.session_state['selected_previous_roadmap'] = selected_roadmap

            # Display selected previous roadmap
            if 'selected_previous_roadmap' in st.session_state:
                st.markdown("---")
                selected = st.session_state['selected_previous_roadmap']
                st.markdown(f"## 📋 {selected['learning_goal']}")
                st.markdown(f"*Created on: {selected['created_at'].strftime('%B %d, %Y at %H:%M')}*")
                
                st.markdown(selected['roadmap_content'])
                
                
                # Download button for previous roadmap
                st.download_button(
                    label=f"📥 Download Previous Roadmap",
                    data=selected['roadmap_content'],
                    file_name=f"previous_roadmap_{selected['_id']}.md",
                    mime="text/markdown"
                )
                
                # Clear button to hide the roadmap
                if st.button("❌ Hide Roadmap", key="hide_previous"):
                    del st.session_state['selected_previous_roadmap']
                    st.rerun()

            elif roadmaps_result["status"] == "success":
                st.info("No previous roadmaps found. Generate your first roadmap above!")
            else:
                st.error(f"Error loading previous roadmaps: {roadmaps_result['message']}")

            # Display previously generated roadmap if it exists
            if 'current_roadmap' in st.session_state and not st.button:
                st.markdown("## 🗺️ Your Personalized Learning Roadmap")
                
                st.markdown(st.session_state['current_roadmap'])
                
                # Add a download button for the markdown file with personalized filename
                st.download_button(
                    label=f"📥 Download {user_data.get('name').split()[0]}'s Roadmap", 
                    data=st.session_state['current_roadmap'],
                    file_name=f"{user_data.get('name').lower().replace(' ', '_')}_learning_roadmap.md",
                    mime="text/markdown"
                )
        
        else:
            # Profile doesn't exist yet
            st.info(f"It looks like you haven't completed your profile questionnaire yet, {user_data.get('name', 'there')}.")
            
            if st.button("Complete Your Profile Now"):
                st.session_state['page'] = 'questionnaire'
                st.rerun()
    
    except Exception as e:
        st.error(f"Error retrieving profile: {str(e)}")
        
        # Fallback content
        st.markdown(f"""
        ## Complete Your Profile
        
        To generate a personalized learning roadmap, we need to know more about you, {user_data.get('name', 'there')}.
        Please complete your profile questionnaire first.
        """)
        
        if st.button("Complete Your Profile"):
            st.session_state['page'] = 'questionnaire'
            st.rerun()