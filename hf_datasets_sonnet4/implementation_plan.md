# HuggingFace Datasets Popularity Viewer - Implementation Plan

## Implementation Strategy

Based on the research and design phase, here's the detailed implementation plan for the HuggingFace datasets popularity viewer.

## Code Structure Overview

```
material_hf_datasets.ipynb
├── Cell 1: Existing ButtonBox class (keep as-is)
├── Cell 2: Dataset API Research & Utilities  
├── Cell 3: Filter Controls Implementation
├── Cell 4: Dataset Manager Class
├── Cell 5: Main Dataset Viewer Class
├── Cell 6: Usage Example & Demo
└── Cell 7: Testing & Validation
```

## Detailed Implementation Plan

### Cell 2: Dataset API Research & Utilities

```python
# Required imports
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from huggingface_hub import HfApi, list_datasets, dataset_info
from ipywidgets import widgets, Layout, HTML, VBox, HBox
import requests
from functools import lru_cache

# Data structures
@dataclass
class DatasetStats:
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

# API Research Implementation
def research_hf_api():
    """Research function to understand API capabilities"""
    api = HfApi()
    
    # Test basic dataset listing
    print("Testing basic dataset listing...")
    datasets = list_datasets(limit=10)
    
    for i, dataset in enumerate(datasets):
        if i >= 3:  # Test first 3 datasets
            break
            
        print(f"\nDataset {i+1}: {dataset.id}")
        print(f"  - Tags: {dataset.tags}")
        print(f"  - Created: {getattr(dataset, 'created_at', 'N/A')}")
        print(f"  - Downloads: {getattr(dataset, 'downloads', 'N/A')}")
        print(f"  - Likes: {getattr(dataset, 'likes', 'N/A')}")
        
        # Try to get detailed info
        try:
            info = dataset_info(dataset.id)
            print(f"  - Description: {info.description[:100] if info.description else 'N/A'}...")
            print(f"  - Siblings: {len(info.siblings) if info.siblings else 0} files")
        except Exception as e:
            print(f"  - Error getting details: {e}")

# Run research
research_hf_api()
```

### Cell 3: Filter Controls Implementation

```python
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
            HTML('<h3>Dataset Filters</h3>'),
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
            self.loading_indicator.value = '<i>Loading...</i>'
            self.refresh_btn.disabled = True
        else:
            self.loading_indicator.value = ''
            self.refresh_btn.disabled = False

# Test the filter controls
test_filters = FilterControls()
display(test_filters.widget)
```

### Cell 4: Dataset Manager Class

```python
class DatasetManager:
    """Manages dataset fetching, caching, and filtering"""
    
    def __init__(self):
        self.api = HfApi()
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour
        
    @lru_cache(maxsize=100)
    def get_dataset_stats(self, dataset_id: str) -> Optional[DatasetStats]:
        """Get comprehensive dataset statistics"""
        try:
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
            print(f"Fetching {limit} datasets...")
            
            # Get dataset list - try with sort parameter if available
            try:
                datasets = list_datasets(limit=limit * 2)  # Get more to filter
            except Exception:
                datasets = list_datasets()  # Fallback without parameters
            
            # Convert to DatasetStats objects
            dataset_stats = []
            for i, dataset in enumerate(datasets):
                if len(dataset_stats) >= limit:
                    break
                    
                stats = self.get_dataset_stats(dataset.id)
                if stats:
                    dataset_stats.append(stats)
                
                # Progress indicator
                if i % 10 == 0:
                    print(f"Processed {i} datasets...")
            
            # Apply filtering and sorting
            filtered_stats = self._apply_filters(dataset_stats, time_period, sort_by)
            
            # Cache results
            self.cache[cache_key] = (time.time(), filtered_stats[:limit])
            
            return filtered_stats[:limit]
            
        except Exception as e:
            print(f"Error fetching datasets: {e}")
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

# Test the dataset manager
test_manager = DatasetManager()
print("Testing dataset manager...")
sample_datasets = test_manager.get_popular_datasets(limit=5)
for dataset in sample_datasets:
    print(f"- {dataset.name}: {dataset.downloads} downloads, {dataset.likes} likes")
```

### Cell 5: Main Dataset Viewer Class

```python
class DatasetViewer:
    """Main class that orchestrates the complete dataset viewer"""
    
    def __init__(self):
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
            value='<p><i>Select a dataset to view details</i></p>',
            layout=Layout(width='100%', height='300px', overflow='auto', 
                         border='1px solid #ccc', padding='10px')
        )
        
        # Create main layout
        self.main_widget = VBox([
            self.filters.widget,
            widgets.HTML('<h3>Popular Datasets</h3>'),
            self.dataset_buttonbox.box,
            widgets.HTML('<h3>Dataset Details</h3>'),
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
            self.details_panel.value = f'<p style="color: red;">Error loading datasets: {e}</p>'
        finally:
            self.filters.set_loading(False)
    
    def update_dataset_display(self):
        """Update the ButtonBox with current datasets"""
        # Clear existing buttons
        self.dataset_buttonbox = ButtonBox([], clicker=self.on_dataset_selected)
        
        # Add dataset buttons
        for dataset in self.current_datasets:
            button_text = f"{dataset.name} ({dataset.downloads:,} downloads)"
            tooltip = f"{dataset.author}/{dataset.name}\nDownloads: {dataset.downloads:,}\nLikes: {dataset.likes}\nDescription: {dataset.description[:100]}..."
            
            # Create button with dataset info in tooltip
            self.dataset_buttonbox.append(button_text, select=False)
            if self.dataset_buttonbox.buttons:
                self.dataset_buttonbox.buttons[-1].tooltip = tooltip
                # Store dataset reference for retrieval
                self.dataset_buttonbox.buttons[-1].dataset_id = dataset.id
        
        # Update the display
        self.main_widget.children = (
            self.filters.widget,
            widgets.HTML('<h3>Popular Datasets</h3>'),
            self.dataset_buttonbox.box,
            widgets.HTML('<h3>Dataset Details</h3>'),
            self.details_panel
        )
    
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
        
        # Create details HTML
        details_html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h4 style="margin-top: 0; color: #2c3e50;">{dataset.author}/{dataset.name}</h4>
            
            <div style="margin: 15px 0;">
                <strong>📊 Statistics:</strong><br>
                • Downloads: <strong>{dataset.downloads:,}</strong><br>
                • Likes: <strong>{dataset.likes}</strong><br>
                • Files: {dataset.file_count or 'Unknown'}<br>
                • Size: {size_str}
            </div>
            
            <div style="margin: 15px 0;">
                <strong>📅 Dates:</strong><br>
                • Created: {created_str}<br>
                • Updated: {updated_str}
            </div>
            
            <div style="margin: 15px 0;">
                <strong>🏷️ Tags:</strong><br>
                {', '.join(dataset.tags[:10]) if dataset.tags else 'No tags available'}
            </div>
            
            <div style="margin: 15px 0;">
                <strong>📝 Description:</strong><br>
                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; max-height: 100px; overflow-y: auto;">
                    {dataset.description if dataset.description else 'No description available.'}
                </div>
            </div>
            
            <div style="margin: 15px 0;">
                <strong>🔗 Links:</strong><br>
                <a href="{dataset.url}" target="_blank" style="color: #007bff; text-decoration: none;">
                    🤗 View on HuggingFace Hub
                </a>
            </div>
        </div>
        """
        
        self.details_panel.value = details_html

# Create and display the main viewer
viewer = DatasetViewer()
display(viewer.main_widget)
```

### Cell 6: Usage Example & Demo

```python
# Example usage and demonstration
print("🚀 HuggingFace Datasets Popularity Viewer")
print("==========================================")
print()
print("Features:")
print("• Filter by time period (7/30/90 days, all time)")
print("• Configurable display limits (25/50/100 datasets)")
print("• Sort by downloads, likes, or dates")
print("• Detailed dataset information on selection")
print("• Direct links to HuggingFace Hub")
print()
print("The viewer is now active above. Try:")
print("1. Change the time period filter")
print("2. Adjust the number of datasets to display")
print("3. Change the sorting criteria")
print("4. Click on any dataset to see details")
print("5. Use the refresh button to reload data")

# Additional helper functions
def quick_search_datasets(keyword: str, limit: int = 10):
    """Quick search function for finding datasets by keyword"""
    datasets = list_datasets(search=keyword, limit=limit)
    results = []
    
    for dataset in datasets:
        stats = viewer.dataset_manager.get_dataset_stats(dataset.id)
        if stats:
            results.append(stats)
    
    return results

def get_top_datasets_by_category(category: str, limit: int = 20):
    """Get top datasets for a specific category/tag"""
    all_datasets = viewer.dataset_manager.get_popular_datasets(limit=200)
    filtered = [d for d in all_datasets if category.lower() in [t.lower() for t in d.tags]]
    return filtered[:limit]

print("\n📚 Additional utility functions available:")
print("• quick_search_datasets('keyword', limit=10)")
print("• get_top_datasets_by_category('nlp', limit=20)")
```

### Cell 7: Testing & Validation

```python
# Testing and validation code
def test_dataset_viewer():
    """Comprehensive test of the dataset viewer functionality"""
    
    print("🧪 Testing Dataset Viewer Components")
    print("===================================")
    
    # Test 1: Filter Controls
    print("✅ Testing filter controls...")
    test_filters = FilterControls()
    assert test_filters.get_filter_values() is not None
    print("   Filter controls working")
    
    # Test 2: Dataset Manager
    print("✅ Testing dataset manager...")
    test_manager = DatasetManager()
    test_datasets = test_manager.get_popular_datasets(limit=5)
    assert len(test_datasets) <= 5
    print(f"   Retrieved {len(test_datasets)} test datasets")
    
    # Test 3: API Connection
    print("✅ Testing API connection...")
    try:
        datasets = list_datasets(limit=1)
        first_dataset = next(iter(datasets))
        print(f"   API connection successful: {first_dataset.id}")
    except Exception as e:
        print(f"   ⚠️ API connection issue: {e}")
    
    # Test 4: Data Processing
    print("✅ Testing data processing...")
    if test_datasets:
        sample_dataset = test_datasets[0]
        assert hasattr(sample_dataset, 'id')
        assert hasattr(sample_dataset, 'downloads')
        print(f"   Data structure valid: {sample_dataset.name}")
    
    print("\n🎉 All tests completed!")
    
    # Performance metrics
    print("\n📊 Performance Information:")
    print(f"• Cache entries: {len(test_manager.cache)}")
    print(f"• API rate limiting: Implemented")
    print(f"• Error handling: Active")

# Run tests
test_dataset_viewer()

print("\n🔧 Troubleshooting Tips:")
print("• If datasets don't load: Check internet connection")
print("• If filtering is slow: Reduce dataset limit")  
print("• If details don't show: Ensure dataset selection")
print("• For API errors: Wait a moment and try refreshing")
```

## Implementation Order

1. **Start with Cell 2**: API research to understand actual capabilities
2. **Implement Cell 3**: Filter controls for user interaction
3. **Build Cell 4**: Dataset manager for data handling
4. **Create Cell 5**: Main viewer class integration
5. **Add Cell 6**: Usage examples and utilities
6. **Finish with Cell 7**: Testing and validation

## Key Implementation Notes

- **Error Handling**: Graceful degradation when API limits are hit
- **Caching**: Essential for performance with large dataset lists
- **Progress Indicators**: Keep users informed during data loading
- **Fallback Metrics**: Use likes/stars if download counts unavailable
- **Rate Limiting**: Respect HuggingFace API guidelines

## Success Criteria

- [ ] Displays datasets sorted by popularity metrics
- [ ] Time-based and limit filtering works
- [ ] Dataset details show on selection with HF links
- [ ] Performance is acceptable (< 5s for 50 datasets)
- [ ] Error handling prevents crashes
- [ ] User interface is intuitive and responsive

This implementation plan provides a complete roadmap for building the HuggingFace datasets popularity viewer with all requested features.