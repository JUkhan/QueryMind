Now our task is to configurable some useful chart properties and all the props saved through 'json_config' (like grid props). So that user can set their desired chart props as they want. We have some chart components:
1. pie-chart/donut-chart
2. line-chart
3. bar-chart

once user click on the 'handleEdit()' function of the chart components it fire an event passing id and title like: 'this.onEdit.emit({ id: this.id(), title: this.title() });' and opens the popup on dashboard-container component and we can update the title of chart components.

this time not title only, have many chart related properties, I am using chart.js lib for rendering chart. Please read the chart.js doc and bring some useful properties.