import ipywidgets as widgets
from ipywidgets import Layout, Textarea, Button, VBox, HBox, Dropdown, Output, Box
from huggingface_hub import list_datasets
from datetime import datetime, timedelta
from typing import List, Union, Optional
from IPython.display import display, clear_output
import json

# Import the ButtonBox class from the notebook
class ButtonBox():
    # An alternative for the Tab widget

    def _clicker(self, b):
        # search clicked button and remember
        self.position, self.button = [(i, but) for i, but in enumerate(self.buttons) if b == but][0]

        # unselect (color) all buttons and select new (list of colors here: https://www.quackit.com/css/css_color_codes.cfm)
        self.unselect()
        self.buttons[self.position].style = {'button_color': self.color}

        # fire event
        if self.clicker:
            self.clicker(self)

    def append(self, description, select=True):
        # add new selector button at the end
        b = Button(description=description if len(description) <= self.maxchar else f'{description[:(self.maxchar-3)]}...',
                   layout=Layout(width='auto', height='21px'),
                   tooltip=f'{description}')
        self.buttons.append(b)
        self.box.children = [*self.box.children, b]

        # select new button / bind event
        if select:
            self.button, self.position = b, len(self.buttons) - 1
            self._clicker(b)
        b.on_click(self._clicker)

    def remove(self, position=None):
        # remove selected if no position given
        if not position:
            position = self.position
        if not position or not position < len(self.buttons) or position < 0:
            return

        # clean up
        self.box.children = [*self.box.children[:position],
                             *self.box.children[position+1:]]
        self.buttons = [*self.buttons[:position], *self.buttons[position+1:]]
        self.button, self.position = None, -1

    def unselect(self):
        # unselect all buttons
        for b in self.buttons:
            b.style = {'button_color': None}

    def __init__(self, descriptions, clicker=None, maxchar=60, color='powderblue'):
        # remember stuff - list to set
        self.descriptions = descriptions if len(
            descriptions) == len(set(descriptions)) else set(descriptions)
        self.clicker, self.maxchar, self.color, self.position, self.button = clicker, maxchar, color, -1, None

        # make buttons
        self.buttons = [Button(description=i if len(i) <= maxchar else f'{i[:(maxchar-3)]}...',
                              layout=Layout(width='auto', height='21px'),
                              tooltip=f'{i}')
                        for i in descriptions]

        # put them in a box / bind event
        self.box = Box(layout=Layout(display='flex', flex_flow='wrap'),
                       children=self.buttons)
        for button in self.buttons:
            button.on_click(self._clicker)

# Function to fetch datasets with various sorting and filtering options
def fetch_datasets(sort_by="downloads", limit=50, date_filter=None):
    """
    Fetch datasets from HuggingFace Hub with sorting and filtering options.
    
    Args:
        sort_by (str): How to sort the datasets. Options: "downloads", "trending_score", "last_modified", "created_at"
        limit (int): Maximum number of datasets to fetch
        date_filter (str): Filter by date. Options: "week", "month", "year", None
    
    Returns:
        list: List of DatasetInfo objects
    """
    # Expand properties to get more information
    expand_properties = [
        "downloads", 
        "downloadsAllTime", 
        "description", 
        "tags", 
        "lastModified", 
        "createdAt",
        "likes"
    ]
    
    # Fetch datasets with sorting
    datasets = list_datasets(
        sort=sort_by,
        direction=-1,  # Descending order
        limit=limit,
        expand=expand_properties
    )
    
    # Convert to list for easier handling
    datasets_list = list(datasets)
    
    # Apply date filtering if requested
    if date_filter and sort_by in ["last_modified", "created_at"]:
        cutoff_date = None
        if date_filter == "week":
            cutoff_date = datetime.now() - timedelta(weeks=1)
        elif date_filter == "month":
            cutoff_date = datetime.now() - timedelta(days=30)
        elif date_filter == "year":
            cutoff_date = datetime.now() - timedelta(days=365)
        
        if cutoff_date:
            date_attr = "last_modified" if sort_by == "last_modified" else "created_at"
            datasets_list = [
                ds for ds in datasets_list 
                if getattr(ds, date_attr) and getattr(ds, date_attr).replace(tzinfo=None) > cutoff_date
            ]
    
    return datasets_list

# Function to display dataset details
def display_dataset_details(dataset):
    """
    Display detailed information about a dataset.
    
    Args:
        dataset: DatasetInfo object
    """
    details = f"""
Dataset: {dataset.id}
URL: https://huggingface.co/datasets/{dataset.id}

Downloads (Recent): {dataset.downloads:,}
Downloads (All Time): {dataset.downloads_all_time:,}
Likes: {dataset.likes if hasattr(dataset, 'likes') else 'N/A'}

Last Modified: {dataset.last_modified if dataset.last_modified else 'N/A'}
Created At: {dataset.created_at if dataset.created_at else 'N/A'}

Description:
{dataset.description if dataset.description else 'No description available.'}

Tags:
{', '.join(dataset.tags) if dataset.tags else 'No tags available.'}
    """.strip()
    
    return details

# Main function to create the interactive UI
def create_dataset_explorer():
    """
    Create an interactive UI for exploring HuggingFace datasets.
    """
    # Create UI elements
    sort_dropdown = Dropdown(
        options=[
            ("Most Downloads (All Time)", "downloads"),
            ("Trending", "trending_score"),
            ("Recently Modified", "last_modified"),
            ("Recently Created", "created_at")
        ],
        value="downloads",
        description="Sort by:",
    )
    
    date_filter_dropdown = Dropdown(
        options=[
            ("All Time", None),
            ("Last Week", "week"),
            ("Last Month", "month"),
            ("Last Year", "year")
        ],
        value=None,
        description="Date Filter:",
    )
    
    limit_slider = widgets.IntSlider(
        value=50,
        min=10,
        max=200,
        step=10,
        description="Limit:",
        style={'description_width': 'initial'}
    )
    
    refresh_button = Button(description="Refresh Datasets")
    output_area = Output()
    
    # Create button box for datasets
    buttonbox = ButtonBox([])
    
    # Function to update dataset list
    def update_datasets(sort_by=None, date_filter=None, limit=None):
        with output_area:
            clear_output()
            print("Fetching datasets...")
            
        try:
            datasets = fetch_datasets(
                sort_by=sort_by or sort_dropdown.value,
                limit=limit or limit_slider.value,
                date_filter=date_filter or date_filter_dropdown.value
            )
            
            # Clear existing buttons
            buttonbox.box.children = []
            buttonbox.buttons = []
            buttonbox.position = -1
            buttonbox.button = None
            
            # Add new dataset buttons
            for dataset in datasets:
                # Use dataset ID as button description
                buttonbox.append(dataset.id, select=False)
            
            with output_area:
                clear_output()
                print(f"Showing {len(datasets)} datasets")
                
        except Exception as e:
            with output_area:
                clear_output()
                print(f"Error fetching datasets: {str(e)}")
    
    # Function to handle dataset selection
    def show_dataset_details(bbox):
        dataset_id = bbox.button.tooltip
        with output_area:
            clear_output()
            print("Fetching dataset details...")
            
        try:
            # Find the dataset in our list
            datasets = fetch_datasets(sort_by=sort_dropdown.value, limit=limit_slider.value)
            selected_dataset = None
            for ds in datasets:
                if ds.id == dataset_id:
                    selected_dataset = ds
                    break
            
            if selected_dataset:
                details = display_dataset_details(selected_dataset)
                with output_area:
                    clear_output()
                    print(details)
            else:
                with output_area:
                    clear_output()
                    print(f"Dataset {dataset_id} not found.")
                    
        except Exception as e:
            with output_area:
                clear_output()
                print(f"Error fetching dataset details: {str(e)}")
    
    # Update buttonbox clicker
    buttonbox.clicker = show_dataset_details
    
    # Event handlers
    def on_refresh_clicked(b):
        update_datasets()
    
    def on_sort_changed(change):
        update_datasets(sort_by=change['new'])
        
    def on_date_filter_changed(change):
        update_datasets(date_filter=change['new'])
        
    def on_limit_changed(change):
        update_datasets(limit=change['new'])
    
    # Bind events
    refresh_button.on_click(on_refresh_clicked)
    sort_dropdown.observe(on_sort_changed, names='value')
    date_filter_dropdown.observe(on_date_filter_changed, names='value')
    limit_slider.observe(on_limit_changed, names='value')
    
    # Initial dataset load
    update_datasets()
    
    # Create layout
    controls = HBox([sort_dropdown, date_filter_dropdown, limit_slider, refresh_button])
    
    # Display everything
    display(VBox([
        controls,
        widgets.HTML("<h3>Popular Datasets</h3>"),
        buttonbox.box,
        widgets.HTML("<h3>Dataset Details</h3>"),
        output_area
    ]))

# Run the explorer when the module is imported
if __name__ == "__main__":
    create_dataset_explorer()