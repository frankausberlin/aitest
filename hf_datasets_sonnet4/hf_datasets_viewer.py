"""
HuggingFace Datasets Popularity Viewer

A comprehensive widget for displaying and exploring the most popular HuggingFace datasets
with filtering capabilities based on download statistics and time periods.

Author: Assistant
Created: 2025-08-20
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from functools import lru_cache

# Required imports
try:
    from huggingface_hub import HfApi, list_datasets, dataset_info
    from ipywidgets import widgets, Layout, HTML, VBox, HBox, Button, Box
    import requests
    HF_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")
    HF_AVAILABLE = False

# Data structures for dataset information
@dataclass
class DatasetStats:
    """Comprehensive dataset statistics and information"""
    id: str
    author: str
    name: str
    description: str
    downloads: int  # Total downloads (proxy if not available)
    likes: int      # HF likes/stars
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    url: str
    size_bytes: Optional[int] = None
    file_count: Optional[int] = None

class ButtonBox:
    """Enhanced ButtonBox class (copy from original with improvements)"""
    
    def _clicker(self, b):
        # search clicked button and remember
        self.position, self.button = [(i, but) for i, but in enumerate(self.buttons) if b == but][0]
        
        # unselect (color) all buttons and select new
        self.unselect()
        self.buttons[self.position].style = {'button_color': self.color}
        
        # fire event
        if self.clicker:
            self.clicker(self)
    
    def append(self, description, select=True):
        # add new selector button at the end
        b = Button(
            description=description if len(description) <= self.maxchar else f'{description[:(self.maxchar-3)]}...',
            layout=Layout(width='auto', height='21px'),
            tooltip=f'{description}'
        )
        
        self.buttons.append(b)
        self.box.children = [*self.box.children, b]
        
        # select new button / bind event
        if select:
            self.button, self.position = b, len(self.buttons) - 1
            self._clicker(b)
        
        b.on_click(self._clicker)
        return b  # Return the button for additional customization
    
    def remove(self, position=None):
        # remove selected if no position given
        if not position:
            position = self.position
        if not position or not position < len(self.buttons) or position < 0:
            return
        
        # clean up
        self.box.children = [*self.box.children[:position], *self.box.children[position+1:]]
        self.buttons = [*self.buttons[:position], *self.buttons[position+1:]]
        self.button, self.position = None, -1
    
    def unselect(self):
        # unselect all buttons
        for b in self.buttons:
            b.style = {'button_color': None}
    
    def clear(self):
        """Clear all buttons"""
        self.buttons = []
        self.box.children = []
        self.button, self.position = None, -1
    
    def __init__(self, descriptions, clicker=None, maxchar=60, color='powderblue'):
        # remember stuff - list to set
        self.descriptions = descriptions if len(descriptions) == len(set(descriptions)) else set(descriptions)
        self.clicker, self.maxchar, self.color, self.position, self.button = clicker, maxchar, color, -1, None
        
        # make buttons
        self.buttons = [
            Button(
                description=i if len(i) <= maxchar else f'{i[:(maxchar-3)]}...',
                layout=Layout(width='auto', height='21px'),
                tooltip=f'{i}'
            )
            for i in descriptions
        ]
        
        # put them in a box / bind event
        self.box = Box(
            layout=Layout(display='flex', flex_flow='wrap'),
            children=self.buttons
        )
        for button in self.buttons:
            button.on_click(self._clicker)

class FilterControls:
    """Widget for dataset filtering controls"""
    
    def __init__(self, on_change_callback=None):
        self.on_change_callback = on_change_callback
        self.setup_widgets()
        
    def setup_widgets(self):
        # Time period filter
        self.time_filter = widgets.RadioButtons(
            options=[
                ('Last 7 days', '7d'),
                ('Last 30 days', '30d'), 
                ('Last 90 days', '90d'),
                ('All time', 'all')
            ],
            value='all',
            description='Time Period:',
            layout=Layout(width='200px')
        )
        
        # Display limit control
        self.limit_filter = widgets.RadioButtons(
            options=[('25 datasets', 25), ('50 datasets', 50), ('100 datasets', 100)],
            value=50,
            description='Show:',
            layout=Layout(width='200px')
        )
        
        # Sort options
        self.sort_filter = widgets.Dropdown(
            options=[
                ('Most Downloads', 'downloads'),
                ('Most Liked', 'likes'),
                ('Recently Updated', 'updated'),
                ('Recently Created', 'created')
            ],
            value='downloads',
            description='Sort by:',
            layout=Layout(width='200px')
        )
        
        # Refresh button
        self.refresh_btn = widgets.Button(
            description='Refresh Data',
            button_style='primary',
            layout=Layout(width='120px', height='32px')
        )
        
        # Loading indicator
        self.loading_indicator = widgets.HTML(
            value='',
            layout=Layout(width='100px')
        )
        
        # Bind events
        self.time_filter.observe(self._on_filter_change, names='value')
        self.limit_filter.observe(self._on_filter_change, names='value')
        self.sort_filter.observe(self._on_filter_change, names='value')
        self.refresh_btn.on_click(self._on_refresh_click)
        
        # Create layout
        self.widget = VBox([
            HTML('<h3 style="color: #2c3e50; margin-bottom: 10px;">🚀 HuggingFace Datasets Popularity Viewer</h3>'),
            HTML('<div style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px;"><b>Filter Options:</b> Choose time period, display limit, and sorting criteria</div>'),
            HBox([self.time_filter, self.limit_filter, self.sort_filter]),
            HBox([self.refresh_btn, self.loading_indicator])
        ])
    
    def _on_filter_change(self, change):
        if self.on_change_callback:
            self.on_change_callback(self.get_filter_values())
    
    def _on_refresh_click(self, button):
        if self.on_change_callback:
            self.on_change_callback(self.get_filter_values(), force_refresh=True)
    
    def get_filter_values(self):
        return {
            'time_period': self.time_filter.value,
            'limit': self.limit_filter.value,
            'sort_by': self.sort_filter.value
        }
    
    def set_loading(self, loading=True):
        if loading:
            self.loading_indicator.value = '<i style="color: #007bff;">⏳ Loading...</i>'
            self.refresh_btn.disabled = True
        else:
            self.loading_indicator.value = '✅ <i style="color: green;">Ready</i>'
            self.refresh_btn.disabled = False

class DatasetManager:
    """Manages dataset fetching, caching, and filtering"""
    
    def __init__(self):
        if not HF_AVAILABLE:
            raise ImportError("HuggingFace Hub library not available. Please install: pip install huggingface_hub")
        
        self.api = HfApi()
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour
        self._stats_cache = {}  # Cache for individual dataset stats
        
    @lru_cache(maxsize=100)
    def get_dataset_stats(self, dataset_id: str) -> Optional[DatasetStats]:
        """Get comprehensive dataset statistics"""
        try:
            # Check cache first
            if dataset_id in self._stats_cache:
                cache_time, stats = self._stats_cache[dataset_id]
                if time.time() - cache_time < self.cache_timeout:
                    return stats
            
            # Get basic dataset info
            info = dataset_info(dataset_id)
            
            # Extract available information
            stats = DatasetStats(
                id=dataset_id,
                author=dataset_id.split('/')[0] if '/' in dataset_id else 'unknown',
                name=dataset_id.split('/')[-1],
                description=getattr(info, 'description', '') or '',
                downloads=getattr(info, 'downloads', 0) or 0,
                likes=getattr(info, 'likes', 0) or 0,
                created_at=getattr(info, 'created_at', datetime.now()),
                updated_at=getattr(info, 'last_modified', datetime.now()) or datetime.now(),
                tags=getattr(info, 'tags', []) or [],
                url=f"https://huggingface.co/datasets/{dataset_id}",
                size_bytes=getattr(info, 'size_in_bytes', None),
                file_count=len(getattr(info, 'siblings', [])) if hasattr(info, 'siblings') else None
            )
            
            # Cache the result
            self._stats_cache[dataset_id] = (time.time(), stats)
            return stats
            
        except Exception as e:
            print(f"Error fetching stats for {dataset_id}: {e}")
            return None
    
    def get_popular_datasets(self, 
                           time_period: str = 'all',
                           limit: int = 50,
                           sort_by: str = 'downloads') -> List[DatasetStats]:
        """Get popular datasets with filtering"""
        
        cache_key = f"{time_period}_{limit}_{sort_by}"
        
        # Check cache
        if cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_timeout:
                return data
        
        try:
            # Fetch datasets from HuggingFace
            print(f"🔍 Fetching {limit} datasets from HuggingFace Hub...")
            
            # Get dataset list - try with sort parameter if available
            try:
                # Try to get more datasets to have better filtering options
                datasets = list_datasets(limit=limit * 3)
            except Exception:
                datasets = list_datasets()  # Fallback without parameters
            
            # Convert to DatasetStats objects with progress indication
            dataset_stats = []
            processed = 0
            
            for dataset in datasets:
                if len(dataset_stats) >= limit:
                    break
                    
                stats = self.get_dataset_stats(dataset.id)
                if stats:
                    dataset_stats.append(stats)
                
                processed += 1
                # Progress indicator every 20 datasets
                if processed % 20 == 0:
                    print(f"  📊 Processed {processed} datasets, found {len(dataset_stats)} with valid stats...")
            
            # Apply filtering and sorting
            filtered_stats = self._apply_filters(dataset_stats, time_period, sort_by)
            
            # Cache results
            self.cache[cache_key] = (time.time(), filtered_stats[:limit])
            
            print(f"✅ Found {len(filtered_stats[:limit])} datasets matching criteria")
            return filtered_stats[:limit]
            
        except Exception as e:
            print(f"❌ Error fetching datasets: {e}")
            return []
    
    def _apply_filters(self, 
                      datasets: List[DatasetStats], 
                      time_period: str, 
                      sort_by: str) -> List[DatasetStats]:
        """Apply time and sorting filters"""
        
        # Time filtering
        if time_period != 'all':
            cutoff_date = datetime.now()
            if time_period == '7d':
                cutoff_date -= timedelta(days=7)
            elif time_period == '30d':
                cutoff_date -= timedelta(days=30)
            elif time_period == '90d':
                cutoff_date -= timedelta(days=90)
            
            # Filter by update date as proxy for recent activity
            datasets = [d for d in datasets if d.updated_at >= cutoff_date]
        
        # Sorting
        if sort_by == 'downloads':
            datasets.sort(key=lambda x: x.downloads, reverse=True)
        elif sort_by == 'likes':
            datasets.sort(key=lambda x: x.likes, reverse=True)
        elif sort_by == 'updated':
            datasets.sort(key=lambda x: x.updated_at, reverse=True)
        elif sort_by == 'created':
            datasets.sort(key=lambda x: x.created_at, reverse=True)
        
        return datasets

class DatasetViewer:
    """Main class that orchestrates the complete dataset viewer"""
    
    def __init__(self):
        if not HF_AVAILABLE:
            raise ImportError("HuggingFace Hub library not available. Please install: pip install huggingface_hub")
            
        self.dataset_manager = DatasetManager()
        self.current_datasets = []
        self.setup_ui()
        
    def setup_ui(self):
        # Create filter controls
        self.filters = FilterControls(on_change_callback=self.on_filters_changed)
        
        # Create dataset button box (initially empty)
        self.dataset_buttonbox = ButtonBox([], clicker=self.on_dataset_selected)
        
        # Create details display
        self.details_panel = widgets.HTML(
            value='''
            <div style="padding: 20px; text-align: center; background: #f8f9fa; border-radius: 10px;">
                <h4 style="color: #6c757d; margin: 0;">📋 Dataset Details</h4>
                <p style="color: #6c757d; margin: 10px 0;">Select a dataset from the list above to view detailed information</p>
                <i style="color: #adb5bd;">Waiting for selection...</i>
            </div>
            ''',
            layout=Layout(width='100%', height='400px', overflow='auto', 
                         border='1px solid #dee2e6', padding='0px', margin='10px 0')
        )
        
        # Create main layout
        self.main_widget = VBox([
            self.filters.widget,
            HTML('<h3 style="color: #2c3e50; margin: 20px 0 10px 0;">📊 Popular Datasets</h3>'),
            HTML('<div style="margin-bottom: 10px; color: #6c757d; font-size: 14px;">Click on any dataset below to view detailed information:</div>'),
            self.dataset_buttonbox.box,
            self.details_panel
        ])
        
        # Load initial data
        self.refresh_datasets()
    
    def on_filters_changed(self, filter_values, force_refresh=False):
        """Handle filter changes"""
        if force_refresh or not self.current_datasets:
            self.refresh_datasets(filter_values)
    
    def refresh_datasets(self, filter_values=None):
        """Refresh the dataset list"""
        if not filter_values:
            filter_values = self.filters.get_filter_values()
        
        self.filters.set_loading(True)
        
        # Clear current display
        self.dataset_buttonbox.clear()
        self.details_panel.value = '''
        <div style="padding: 20px; text-align: center;">
            <h4 style="color: #007bff;">⏳ Loading Datasets...</h4>
            <p>Fetching popular datasets from HuggingFace Hub...</p>
        </div>
        '''
        
        try:
            # Fetch datasets
            datasets = self.dataset_manager.get_popular_datasets(
                time_period=filter_values['time_period'],
                limit=filter_values['limit'],
                sort_by=filter_values['sort_by']
            )
            
            self.current_datasets = datasets
            self.update_dataset_display()
            
        except Exception as e:
            self.details_panel.value = f'''
            <div style="padding: 20px; text-align: center; color: red;">
                <h4>❌ Error Loading Datasets</h4>
                <p>Error: {e}</p>
                <p>Please check your internet connection and try again.</p>
            </div>
            '''
        finally:
            self.filters.set_loading(False)
    
    def update_dataset_display(self):
        """Update the ButtonBox with current datasets"""
        # Clear existing buttons
        self.dataset_buttonbox.clear()
        
        if not self.current_datasets:
            self.details_panel.value = '''
            <div style="padding: 20px; text-align: center;">
                <h4 style="color: #ffc107;">⚠️ No Datasets Found</h4>
                <p>No datasets match the current filter criteria.</p>
                <p>Try adjusting the filters or refresh the data.</p>
            </div>
            '''
            return
        
        # Add dataset buttons
        for i, dataset in enumerate(self.current_datasets):
            # Format download count
            download_str = f"{dataset.downloads:,}" if dataset.downloads > 0 else "N/A"
            
            # Create button text with ranking
            button_text = f"#{i+1} {dataset.name} ({download_str} downloads)"
            
            # Create comprehensive tooltip
            tooltip = f"""Dataset: {dataset.author}/{dataset.name}
Downloads: {download_str}
Likes: {dataset.likes}
Tags: {', '.join(dataset.tags[:5]) if dataset.tags else 'None'}
Updated: {dataset.updated_at.strftime('%Y-%m-%d') if dataset.updated_at else 'Unknown'}
Description: {dataset.description[:150] if dataset.description else 'No description available'}..."""
            
            # Add button with dataset info
            btn = self.dataset_buttonbox.append(button_text, select=False)
            btn.tooltip = tooltip
            btn.dataset_id = dataset.id  # Store dataset reference
            
        # Update success message
        self.details_panel.value = f'''
        <div style="padding: 20px; text-align: center; background: #d4edda; border-radius: 10px;">
            <h4 style="color: #155724; margin: 0;">✅ {len(self.current_datasets)} Datasets Loaded</h4>
            <p style="color: #155724; margin: 10px 0;">Click on any dataset above to view detailed information</p>
        </div>
        '''
    
    def on_dataset_selected(self, buttonbox):
        """Handle dataset selection"""
        if buttonbox.button and hasattr(buttonbox.button, 'dataset_id'):
            dataset_id = buttonbox.button.dataset_id
            dataset = next((d for d in self.current_datasets if d.id == dataset_id), None)
            
            if dataset:
                self.display_dataset_details(dataset)
    
    def display_dataset_details(self, dataset: DatasetStats):
        """Display detailed information for selected dataset"""
        
        # Format file size
        size_str = "Unknown"
        if dataset.size_bytes:
            if dataset.size_bytes > 1e9:
                size_str = f"{dataset.size_bytes / 1e9:.1f} GB"
            elif dataset.size_bytes > 1e6:
                size_str = f"{dataset.size_bytes / 1e6:.1f} MB"
            else:
                size_str = f"{dataset.size_bytes / 1e3:.1f} KB"
        
        # Format dates
        created_str = dataset.created_at.strftime('%Y-%m-%d') if dataset.created_at else 'Unknown'
        updated_str = dataset.updated_at.strftime('%Y-%m-%d') if dataset.updated_at else 'Unknown'
        
        # Format tags
        tags_html = ""
        if dataset.tags:
            tags_html = "".join([f'<span style="background: #e3f2fd; color: #1976d2; padding: 2px 6px; margin: 2px; border-radius: 3px; font-size: 12px;">{tag}</span> ' for tag in dataset.tags[:10]])
        else:
            tags_html = '<span style="color: #999;">No tags available</span>'
        
        # Create details HTML
        details_html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; background: white; border-radius: 10px;">
            <div style="border-bottom: 2px solid #007bff; padding-bottom: 15px; margin-bottom: 20px;">
                <h3 style="margin: 0; color: #007bff;">📊 {dataset.author}/{dataset.name}</h3>
                <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 14px;">Dataset Details & Statistics</p>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <h4 style="margin: 0 0 10px 0; color: #2c3e50;">📈 Statistics</h4>
                    <div style="line-height: 1.6;">
                        <strong>Downloads:</strong> <span style="color: #28a745; font-weight: bold;">{dataset.downloads:,}</span><br>
                        <strong>Likes:</strong> <span style="color: #ffc107; font-weight: bold;">❤️ {dataset.likes}</span><br>
                        <strong>Files:</strong> {dataset.file_count or 'Unknown'}<br>
                        <strong>Size:</strong> {size_str}
                    </div>
                </div>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <h4 style="margin: 0 0 10px 0; color: #2c3e50;">📅 Timeline</h4>
                    <div style="line-height: 1.6;">
                        <strong>Created:</strong> {created_str}<br>
                        <strong>Updated:</strong> {updated_str}
                    </div>
                </div>
            </div>
            
            <div style="margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #2c3e50;">🏷️ Tags</h4>
                <div style="line-height: 1.8;">
                    {tags_html}
                </div>
            </div>
            
            <div style="margin: 20px 0;">
                <h4 style="margin: 0 0 10px 0; color: #2c3e50;">📝 Description</h4>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; max-height: 120px; overflow-y: auto; line-height: 1.5;">
                    {dataset.description if dataset.description else '<i style="color: #999;">No description available for this dataset.</i>'}
                </div>
            </div>
            
            <div style="margin: 20px 0 0 0; text-align: center;">
                <a href="{dataset.url}" target="_blank" 
                   style="display: inline-block; background: #007bff; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 6px; font-weight: bold; 
                          transition: background 0.3s;">
                    🤗 View on HuggingFace Hub
                </a>
            </div>
        </div>
        """
        
        self.details_panel.value = details_html

# Utility functions for quick access
def quick_search_datasets(keyword: str, limit: int = 10) -> List[DatasetStats]:
    """Quick search function for finding datasets by keyword"""
    if not HF_AVAILABLE:
        print("HuggingFace Hub not available")
        return []
    
    try:
        datasets = list_datasets(search=keyword, limit=limit)
        manager = DatasetManager()
        results = []
        
        for dataset in datasets:
            stats = manager.get_dataset_stats(dataset.id)
            if stats:
                results.append(stats)
        
        return results
    except Exception as e:
        print(f"Error searching datasets: {e}")
        return []

def get_top_datasets_by_category(category: str, limit: int = 20) -> List[DatasetStats]:
    """Get top datasets for a specific category/tag"""
    if not HF_AVAILABLE:
        print("HuggingFace Hub not available")
        return []
    
    try:
        manager = DatasetManager()
        all_datasets = manager.get_popular_datasets(limit=200)
        filtered = [d for d in all_datasets if category.lower() in [t.lower() for t in d.tags]]
        return filtered[:limit]
    except Exception as e:
        print(f"Error getting datasets by category: {e}")
        return []

# Research function
def research_hf_api():
    """Research function to understand API capabilities"""
    if not HF_AVAILABLE:
        print("❌ HuggingFace Hub library not available")
        return
    
    print("🔍 Researching HuggingFace Hub API capabilities...")
    
    try:
        # Test basic dataset listing
        print("Testing basic dataset listing...")
        datasets = list_datasets(limit=5)
        
        for i, dataset in enumerate(datasets):
            if i >= 3:  # Test first 3 datasets
                break
                
            print(f"\nDataset {i+1}: {dataset.id}")
            print(f"  - Tags: {getattr(dataset, 'tags', 'N/A')}")
            print(f"  - Created: {getattr(dataset, 'created_at', 'N/A')}")
            print(f"  - Downloads: {getattr(dataset, 'downloads', 'N/A')}")
            print(f"  - Likes: {getattr(dataset, 'likes', 'N/A')}")
            
            # Try to get detailed info
            try:
                info = dataset_info(dataset.id)
                desc = getattr(info, 'description', None)
                print(f"  - Description: {desc[:100] if desc else 'N/A'}...")
                print(f"  - Siblings: {len(getattr(info, 'siblings', [])) if hasattr(info, 'siblings') else 0} files")
            except Exception as e:
                print(f"  - Error getting details: {e}")
        
        print("\n✅ API research completed!")
        
    except Exception as e:
        print(f"❌ Error during API research: {e}")

def test_viewer():
    """Test function for the dataset viewer"""
    print("🧪 Testing HuggingFace Dataset Viewer...")
    
    if not HF_AVAILABLE:
        print("❌ Cannot test - HuggingFace Hub library not available")
        return
    
    try:
        # Test API connection
        print("✅ Testing API connection...")
        datasets = list_datasets(limit=1)
        first_dataset = next(iter(datasets))
        print(f"   API connection successful: {first_dataset.id}")
        
        # Test DatasetManager
        print("✅ Testing DatasetManager...")
        manager = DatasetManager()
        test_datasets = manager.get_popular_datasets(limit=3)
        print(f"   Retrieved {len(test_datasets)} datasets")
        
        if test_datasets:
            print("   Sample dataset:", test_datasets[0].name)
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

# Main execution
if __name__ == "__main__":
    print("HuggingFace Datasets Popularity Viewer")
    print("======================================")
    print()
    
    if HF_AVAILABLE:
        print("✅ All dependencies available")
        print("You can now create a DatasetViewer instance:")
        print("  viewer = DatasetViewer()")
        print("  display(viewer.main_widget)")
    else:
        print("❌ Missing dependencies. Please install:")
        print("  pip install huggingface_hub ipywidgets")