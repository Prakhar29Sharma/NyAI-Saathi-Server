document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const activeQueryElement = document.getElementById('activeQuery');
    const responseContainer = document.getElementById('responseContainer');
    const pipelineStatus = document.getElementById('pipelineStatus');
    const totalTimeDisplay = document.getElementById('totalTimeDisplay');
    const connectionStatus = document.getElementById('connectionStatus');
    const pipelineTypeLabel = document.getElementById('pipelineTypeLabel');
    const userIdLabel = document.getElementById('userIdLabel');
    const ganttTotalTime = document.getElementById('ganttTotalTime');
    const toggleResponseBtn = document.getElementById('toggleResponseBtn');
    const timelineMetrics = document.getElementById('timelineMetrics');
    const queryTimestamp = document.getElementById('queryTimestamp');
    const metricValues = {
        embedding: {
            time: document.getElementById('embeddingTimeValue'),
            percent: document.getElementById('embeddingPercentValue')
        },
        search: {
            time: document.getElementById('searchTimeValue'),
            percent: document.getElementById('searchPercentValue')
        },
        context: {
            time: document.getElementById('contextTimeValue'),
            percent: document.getElementById('contextPercentValue')
        },
        llm: {
            time: document.getElementById('llmTimeValue'),
            percent: document.getElementById('llmPercentValue')
        }
    };
    
    // Pipeline steps
    const stepElements = {
        query: document.getElementById('step-query'),
        embedding: document.getElementById('step-embedding'),
        retrieval: document.getElementById('step-retrieval'),
        context: document.getElementById('step-context'),
        generation: document.getElementById('step-generation')
    };
    
    // Step details elements
    const detailElements = {
        query: document.getElementById('queryDetails'),
        embedding: document.getElementById('embeddingDetails'),
        retrieval: document.getElementById('retrievalDetails'),
        context: document.getElementById('contextDetails'),
        generation: document.getElementById('generationDetails')
    };
    
    // Metrics elements
    const metricElements = {
        embedding: {
            time: document.getElementById('embeddingTime'),
            status: document.getElementById('embeddingStatus')
        },
        search: {
            time: document.getElementById('searchTime'),
            status: document.getElementById('searchStatus')
        },
        context: {
            time: document.getElementById('contextTime'),
            status: document.getElementById('contextStatus')
        },
        llm: {
            time: document.getElementById('llmTime'),
            status: document.getElementById('llmStatus')
        }
    };

    // Gantt chart
    let ganttChart = null;
    const ganttChartCanvas = document.getElementById('pipelineGanttChart');
    const noDataMessage = document.getElementById('noDataMessage');

    // Add this variable to track chart resize observer
    let chartResizeObserver = null;

    // Variables to track state
    let eventSource = null;
    let pipelineActive = false;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const reconnectDelay = 3000; // 3 seconds

    // Add a variable to store the current query information
    let currentQueryInfo = null;

    function connectToEventStream() {
        if (eventSource) {
            eventSource.close();
        }

        // Update connection status
        connectionStatus.textContent = 'Connecting...';
        connectionStatus.className = 'badge bg-warning';

        // Create the EventSource for SSE connection
        eventSource = new EventSource('/api/v1/pipeline/monitor');
        
        // Add event listeners for connection status
        eventSource.addEventListener('open', (e) => {
            console.log('SSE connection opened');
            connectionStatus.textContent = 'Connected';
            connectionStatus.className = 'status-badge connected';
            reconnectAttempts = 0;
            
            // Add connection animation
            animateElement(connectionStatus);
            
            // Restore UI state when reconnecting
            restoreUIState();
        });
        
        eventSource.addEventListener('error', (e) => {
            console.error('SSE error:', e);
            connectionStatus.textContent = 'Disconnected';
            connectionStatus.className = 'status-badge disconnected';
            
            // Add connection animation
            animateElement(connectionStatus);
            
            // Attempt to reconnect
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                connectionStatus.textContent = `Reconnecting...`;
                setTimeout(connectToEventStream, reconnectDelay);
            } else {
                connectionStatus.textContent = 'Failed to connect';
            }
        });
        
        // Add event listeners for pipeline events
        eventSource.addEventListener('new_query', (e) => {
            try {
                const data = JSON.parse(e.data);
                logEventDetails('new_query', data);
                
                // Store the current query info
                currentQueryInfo = {
                    query: data.query,
                    pipelineType: data.pipeline_type,
                    timestamp: new Date()
                };
                
                // Reset the UI for a new pipeline run
                resetPipelineUI();
                
                // Display the query
                displayActiveQuery(currentQueryInfo.query, currentQueryInfo.pipelineType);
                
                // Update pipeline status
                pipelineStatus.textContent = 'Processing';
                pipelineStatus.className = 'badge bg-warning';
                
                // Update query step
                updateStep('query', 'active', `Processing: "${truncateText(currentQueryInfo.query, 50)}"`);
                
                // Update pipeline active flag
                pipelineActive = true;
            } catch (error) {
                console.error('Error processing new_query event:', error);
            }
        });
        
        // Add event listeners for other pipeline stages
        eventSource.addEventListener('embedding_start', (e) => {
            updateStep('query', 'completed');
            updateStep('embedding', 'active', 'Converting query to vector representation...');
            updateMetric('embedding', 'processing');
        });
        
        eventSource.addEventListener('embedding_complete', (e) => {
            const data = JSON.parse(e.data);
            updateStep('embedding', 'completed', `Generated ${data.vector_size} dimension embedding`);
            updateMetric('embedding', 'completed', data.time_ms);
        });
        
        eventSource.addEventListener('search_start', (e) => {
            updateStep('embedding', 'completed');
            updateStep('retrieval', 'active', 'Searching vector database...');
            updateMetric('search', 'processing');
        });
        
        eventSource.addEventListener('search_complete', (e) => {
            const data = JSON.parse(e.data);
            updateStep('retrieval', 'completed', `Found ${data.results_count} relevant documents`);
            updateMetric('search', 'completed', data.time_ms);
        });
        
        eventSource.addEventListener('context_start', (e) => {
            updateStep('retrieval', 'completed');
            updateStep('context', 'active', 'Building context from retrieved documents...');
            updateMetric('context', 'processing');
        });
        
        eventSource.addEventListener('context_complete', (e) => {
            const data = JSON.parse(e.data);
            updateStep('context', 'completed', `Prepared context with ${data.token_count} tokens`);
            updateMetric('context', 'completed', data.time_ms);
        });
        
        eventSource.addEventListener('llm_start', (e) => {
            updateStep('context', 'completed');
            updateStep('generation', 'active', 'Generating response with Gemini...');
            updateMetric('llm', 'processing');
        });
        
        eventSource.addEventListener('llm_complete', (e) => {
            const data = JSON.parse(e.data);
            updateStep('generation', 'completed', `Generated response with ${data.token_count} tokens`);
            updateMetric('llm', 'completed', data.time_ms);
        });
        
        eventSource.addEventListener('complete', (e) => {
            try {
                const data = JSON.parse(e.data);
                console.log('Complete event received:', data);
                
                // First check if the event contains query information
                if (data.query) {
                    console.log('Query found in complete event:', data.query);
                    
                    // Always update currentQueryInfo regardless of whether it already exists
                    currentQueryInfo = {
                        query: data.query,
                        pipelineType: data.pipeline_type || 'unknown',
                        timestamp: new Date()
                    };
                    
                    // Force an update of the query display
                    displayActiveQuery(data.query, data.pipeline_type);
                } else {
                    console.warn('No query found in complete event');
                }
                
                // Update total time
                totalTimeDisplay.textContent = `${(data.total_time_ms / 1000).toFixed(2)}s`;
                
                // Display the response
                displayResponse(data.answer);
                
                // Update pipeline status
                pipelineStatus.textContent = 'Completed';
                pipelineStatus.className = 'badge bg-success';
                
                // Update the Gantt chart with the pipeline execution data
                updateGanttChart({
                    total_time_ms: data.total_time_ms,
                    embedding_time_ms: data.embedding_time_ms || 0,
                    search_time_ms: data.search_time_ms || 0,
                    context_time_ms: data.context_time_ms || 0,
                    llm_time_ms: data.llm_time_ms || 0
                });
                
                // Reset pipeline active flag
                pipelineActive = false;
            } catch (error) {
                console.error('Error processing complete event:', error);
            }
        });
        
        eventSource.addEventListener('error_occurred', (e) => {
            const data = JSON.parse(e.data);
            handlePipelineError(data.error);
        });
        
        // Ping event to keep connection alive
        eventSource.addEventListener('ping', (e) => {
            console.log('Ping received');
        });
    }

    // Function to display active query
    function displayActiveQuery(query, pipelineType) {
        console.log('Updating active query display:', { query, pipelineType });
        
        if (!query) {
            console.warn('displayActiveQuery called with empty query');
            // If no query is provided, show the waiting state
            activeQueryElement.innerHTML = `
                <div class="placeholder-text text-center text-muted">
                    <i class="bi bi-hourglass fs-2"></i>
                    <p>Waiting for an incoming query...</p>
                </div>
            `;
            pipelineTypeLabel.innerHTML = `Pipeline: <span class="fw-medium">-</span>`;
            queryTimestamp.innerHTML = `Time: <span class="fw-medium">-</span>`;
            return;
        }
        
        // Format the query with proper wrapping
        activeQueryElement.innerHTML = `
            <div class="query-text">${escapeHtml(query)}</div>
        `;
        
        // Update pipeline type label
        pipelineTypeLabel.innerHTML = `Pipeline: <span class="fw-medium">${capitalizeFirstLetter(pipelineType || 'unknown')}</span>`;
        
        // Update timestamp
        const now = currentQueryInfo?.timestamp || new Date();
        const timeString = now.toLocaleTimeString();
        queryTimestamp.innerHTML = `Time: <span class="fw-medium">${timeString}</span>`;
                // Add this function to ensure the logo loads properly and to adjust the UI on startup
        function optimizeAppLayout() {
            // Verify the logo loaded properly
            const logoImage = document.querySelector('.logo-image');
            if (logoImage) {
                logoImage.onerror = function() {
                    console.error('Logo image failed to load');
                    // Fallback to text
                    const logoContainer = document.querySelector('.logo-container');
                    logoContainer.innerHTML = `
                        <div class="logo">
                            <span class="logo-icon"><i class="bi bi-braces-asterisk"></i></span>
                            <h1>NyAI Saathi</h1>
                        </div>
                        <div class="connection-status">
                            <span id="connectionStatus" class="status-badge disconnected">Disconnected</span>
                        </div>
                    `;
                };
            }
            
            // Adjust sidebar height on mobile
            function adjustMobileLayout() {
                if (window.innerWidth <= 992) {
                    document.body.style.overflow = 'auto';
                    document.querySelector('.app-container').style.height = 'auto';
                } else {
                    document.body.style.overflow = 'hidden';
                    document.querySelector('.app-container').style.height = '100vh';
                }
            }
            
            // Initial check
            adjustMobileLayout();
            
            // Add resize listener
            window.addEventListener('resize', adjustMobileLayout);
            
            // Make sure scrolling is smooth
            document.querySelectorAll('.content-section').forEach(section => {
                section.addEventListener('click', function() {
                    this.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                });
            });
        }
        
        // Add staggered animation for a more polished appearance
        function staggeredAnimations() {
            // Animate elements sequentially
            const animateSequentially = (elements, delay, interval) => {
                elements.forEach((el, index) => {
                    animateElement(el, delay + (index * interval));
                });
            };
            
            // Animate sidebar sections
            const sidebarSections = document.querySelectorAll('.sidebar-section');
            animateSequentially(sidebarSections, 100, 80);
            
            // Animate pipeline steps
            const pipelineSteps = document.querySelectorAll('.pipeline-step');
            animateSequentially(pipelineSteps, 200, 50);
            
            // Animate content sections
            const contentSections = document.querySelectorAll('.content-section');
            animateSequentially(contentSections, 150, 100);
        }
        
        // Update the DOM content loaded handler
        document.addEventListener('DOMContentLoaded', function() {
            // Set up the app layout
            optimizeAppLayout();
            
            // Set initial button state
            toggleResponseBtn.style.display = 'none';
            
            // Initialize the chart
            initGanttChart();
            
            // Apply animations
            staggeredAnimations();
            
            // Add tooltip positions for better visibility
            document.addEventListener('mousemove', function(e) {
                const tooltip = document.getElementById('chartjs-tooltip');
                if (tooltip && tooltip.style.opacity !== '0') {
                    // Make sure tooltip doesn't go off-screen
                    const tooltipRect = tooltip.getBoundingClientRect();
                    const windowWidth = window.innerWidth;
                    const windowHeight = window.innerHeight;
                    
                    if (tooltipRect.right > windowWidth) {
                        tooltip.style.left = (windowWidth - tooltipRect.width - 20) + 'px';
                    }
                    
                    if (tooltipRect.bottom > windowHeight) {
                        tooltip.style.top = (windowHeight - tooltipRect.height - 20) + 'px';
                    }
                }
            });
        });
        
        // Keep the rest of your JS code...
        console.log('Active query display updated');
    }

    // Helper function to safely escape HTML content
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Helper function to capitalize the first letter
    function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }

    // Function to update a pipeline step
    function updateStep(stepName, state, details = null) {
        const stepElement = stepElements[stepName];
        const detailElement = detailElements[stepName];
        const spinner = stepElement.querySelector('.spinner');
        const connectors = document.querySelectorAll('.pipeline-connector');
        
        // Remove all state classes
        stepElement.classList.remove('active', 'completed', 'error');
        
        // Add the new state class
        if (state) {
            stepElement.classList.add(state);
            
            // Add ripple effect for state changes
            createRippleEffect(stepElement);
            
            // Animate the connector before this step
            const stepIndex = Object.keys(stepElements).indexOf(stepName);
            if (stepIndex > 0) {
                const connector = connectors[stepIndex - 1];
                if (connector) {
                    if (state === 'active') {
                        connector.classList.add('active');
                    } else if (state === 'completed') {
                        connector.classList.add('active');
                    }
                }
            }
        }
        
        // Update spinner visibility
        if (state === 'active') {
            spinner.style.display = 'block';
        } else {
            spinner.style.display = 'none';
        }
        
        // Update details if provided
        if (details) {
            detailElement.textContent = details;
            animateElement(detailElement, 100);
        }
    }

    // Function to update a metric
    function updateMetric(metricName, state, timeMs = null) {
        const metricElement = metricElements[metricName];
        let statusBadge = '';
        
        switch(state) {
            case 'processing':
                statusBadge = '<span class="badge bg-warning">Processing</span>';
                metricElement.time.textContent = '-';
                break;
            case 'completed':
                statusBadge = '<span class="badge bg-success">Completed</span>';
                metricElement.time.textContent = timeMs ? `${timeMs.toFixed(0)}` : '-';
                break;
            case 'error':
                statusBadge = '<span class="badge bg-danger">Error</span>';
                break;
            default:
                statusBadge = '<span class="badge bg-secondary">Waiting</span>';
        }
        
        metricElement.status.innerHTML = statusBadge;
    }

    // Function to reset the pipeline UI
    function resetPipelineUI() {
        // Reset all steps
        Object.keys(stepElements).forEach(step => {
            updateStep(step, '');
        });
        
        // Reset all metrics
        Object.keys(metricElements).forEach(metric => {
            updateMetric(metric, 'waiting');
            metricElements[metric].time.textContent = '-';
        });
        
        // Do NOT reset the active query if we have one
        // This is key - we want to keep showing the query even after completion
        
        // Reset Gantt chart
        if (ganttChart) {
            ganttChart.data.datasets = [];
            ganttChart.update();
            ganttChartCanvas.style.display = 'none';
            noDataMessage.style.display = 'block';
        }
        
        // Reset total time display
        ganttTotalTime.textContent = 'Total: 0.00s';
        
        // Reset metrics
        timelineMetrics.classList.add('d-none');
        for (const stageKey in metricValues) {
            if (metricValues[stageKey]) {
                metricValues[stageKey].time.textContent = '0 ms';
                metricValues[stageKey].percent.textContent = '0%';
            }
        }
        
        // Reset response toggle button
        toggleResponseBtn.classList.add('d-none');
        responseContainer.classList.remove('expanded', 'response-truncated');
    }

    // Function to handle pipeline errors
    function handlePipelineError(errorMessage) {
        pipelineStatus.textContent = 'Error';
        pipelineStatus.className = 'badge bg-danger';
        
        // Mark current active step as error
        Object.keys(stepElements).forEach(step => {
            if (stepElements[step].classList.contains('active')) {
                updateStep(step, 'error', `Error: ${errorMessage}`);
            }
        });
        
        // Display error in response container
        responseContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill"></i>
                <strong>Error:</strong> ${errorMessage}
            </div>
        `;
        
        // Reset pipeline active flag
        pipelineActive = false;
    }

    // Function to display the response
    function displayResponse(answer) {
        if (!answer || answer.trim() === '') {
            // Show placeholder if no answer
            responseContainer.innerHTML = `
                <div class="placeholder-text">
                    <i class="bi bi-chat-square-text"></i>
                    <p>The response will appear here after processing the query</p>
                </div>
            `;
            toggleResponseBtn.style.display = 'none';
            return;
        }

        // Use marked.js to render markdown
        const htmlContent = marked.parse(answer);
        
        // Create response element with fadeIn effect
        responseContainer.innerHTML = `
            <div class="response-markdown">
                ${htmlContent}
            </div>
        `;
        
        // Add fade-in animation
        const responseMarkdown = responseContainer.querySelector('.response-markdown');
        animateElement(responseMarkdown);
        
        // Reset container state
        responseContainer.classList.remove('expanded', 'response-truncated');
        
        // Check if content needs truncation (after a slight delay to ensure rendering)
        setTimeout(() => {
            checkForTruncation();
        }, 50);
    }

    // Function to check if response should be truncated
    function checkForTruncation() {
        const responseMarkdown = responseContainer.querySelector('.response-markdown');
        
        if (!responseMarkdown) return;
        
        // Get height of container and content
        const containerHeight = responseContainer.clientHeight;
        const contentHeight = responseMarkdown.scrollHeight;
        
        console.log('Container height:', containerHeight);
        console.log('Content height:', contentHeight);
        
        // If content is taller than container, we need truncation
        if (contentHeight > containerHeight - 40) { // 40px buffer
            responseContainer.classList.add('response-truncated');
            toggleResponseBtn.style.display = 'flex';
            // Reset button text
            toggleResponseBtn.innerHTML = '<i class="bi bi-arrows-angle-expand"></i><span>View Full Response</span>';
            console.log('Truncating response');
        } else {
            // No need for truncation
            responseContainer.classList.remove('response-truncated');
            toggleResponseBtn.style.display = 'none';
            console.log('No truncation needed');
        }
    }

    // Improved toggle function with smooth scrolling and animation
    function toggleResponseExpansion() {
        const isExpanded = responseContainer.classList.contains('expanded');
        
        if (isExpanded) {
            // Collapse
            responseContainer.classList.remove('expanded');
            responseContainer.classList.add('response-truncated');
            toggleResponseBtn.innerHTML = '<i class="bi bi-arrows-angle-expand"></i><span>View Full Response</span>';
        } else {
            // Expand
            responseContainer.classList.add('expanded');
            responseContainer.classList.remove('response-truncated');
            toggleResponseBtn.innerHTML = '<i class="bi bi-arrows-angle-contract"></i><span>Show Less</span>';
            
            // Scroll to ensure the expanded content is visible
            setTimeout(() => {
                const responseCard = document.querySelector('.response-card');
                if (responseCard) {
                    responseCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 100);
        }
    }

    // Update the initGanttChart function to properly clean up resources
    function initGanttChart() {
        // Clean up existing resources
        if (ganttChart) {
            ganttChart.destroy();
            ganttChart = null;
        }
        
        // Clean up any existing resize observer
        if (chartResizeObserver) {
            chartResizeObserver.disconnect();
            chartResizeObserver = null;
        }

        // Hide the canvas initially and show the no data message
        ganttChartCanvas.style.display = 'none';
        timelineMetrics.classList.add('d-none');
        noDataMessage.style.display = 'block';

        // Set fixed dimensions for the canvas
        ganttChartCanvas.height = 80;
        
        // Set default configuration
        Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
        
        // Create a horizontal timeline chart
        ganttChart = new Chart(ganttChartCanvas, {
            type: 'bar',
            data: {
                labels: ['Pipeline'],
                datasets: []
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 6,
                layout: {
                    padding: {
                        top: 30,
                        bottom: 5
                    }
                },
                scales: {
                    x: {
                        position: 'top',
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Time (milliseconds)',
                            font: {
                                weight: '600',
                                size: 12
                            }
                        },
                        ticks: {
                            callback: function(value) {
                                return value + ' ms';
                            },
                            font: {
                                size: 11
                            },
                            maxTicksLimit: 8
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    y: {
                        display: false
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false,
                        external: customTooltip
                    }
                }
            }
        });
        
        // Use ResizeObserver to handle resize events efficiently
        chartResizeObserver = new ResizeObserver(debounce(() => {
            if (ganttChart) {
                ganttChart.resize();
            }
        }, 100));
        
        chartResizeObserver.observe(ganttChartCanvas.parentNode);
    }

    // Debounce function to limit how often a function is called
    function debounce(func, wait) {
        let timeout;
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                func.apply(context, args);
            }, wait);
        };
    }

    // Update the updateGanttChart function to be more performance-efficient
    function updateGanttChart(pipelineData) {
        // Make sure we have a chart
        if (!ganttChart) {
            initGanttChart();
        }

        // Show the canvas and metrics, hide the no data message
        ganttChartCanvas.style.display = 'block';
        timelineMetrics.style.display = 'grid';
        noDataMessage.style.display = 'none';

        // Extract timing data from pipeline metrics
        const totalTime = pipelineData.total_time_ms || 0;
        
        // Stage colors
        const stageColors = {
            embedding: 'rgba(54, 162, 235, 0.8)',
            search: 'rgba(255, 159, 64, 0.8)',
            context: 'rgba(75, 192, 192, 0.8)',
            llm: 'rgba(153, 102, 255, 0.8)'
        };
        
        // Update total time display with animation
        ganttTotalTime.textContent = `Total: ${(totalTime / 1000).toFixed(2)}s`;
        animateElement(ganttTotalTime);
        
        // Define all stages with their data
        const stages = [
            {
                name: 'Query Embedding',
                key: 'embedding_time_ms',
                color: stageColors.embedding,
                metricKey: 'embedding'
            },
            {
                name: 'Vector Search',
                key: 'search_time_ms',
                color: stageColors.search,
                metricKey: 'search'
            },
            {
                name: 'Context Building',
                key: 'context_time_ms',
                color: stageColors.context,
                metricKey: 'context'
            },
            {
                name: 'LLM Generation',
                key: 'llm_time_ms',
                color: stageColors.llm,
                metricKey: 'llm'
            }
        ];
        
        // Process stage data and update metrics
        const datasets = [];
        let currentPosition = 0;
        
        // For drawing stage labels above the timeline
        const stagePlugins = [];

        for (const [index, stage] of stages.entries()) {
            const time = pipelineData[stage.key] || 0;
            
            // Calculate percentage of total time
            const percentage = totalTime > 0 ? (time / totalTime) * 100 : 0;
            
            // Update the detailed metrics display below the chart
            if (metricValues[stage.metricKey]) {
                metricValues[stage.metricKey].time.textContent = `${Math.round(time)} ms`;
                metricValues[stage.metricKey].percent.textContent = `${percentage.toFixed(1)}%`;
                
                // Add staggered animation for each metric item
                const metricItem = metricValues[stage.metricKey].time.closest('.metric-item');
                if (metricItem) {
                    animateElement(metricItem, 100 + (index * 50));
                }
            }
            
            // Only add to timeline if there's actual time recorded
            if (time > 0) {
                // For timeline, we need the start position for each stage
                datasets.push({
                    label: stage.name,
                    data: [time],
                    backgroundColor: stage.color,
                    borderColor: 'rgba(255, 255, 255, 0.8)',
                    borderWidth: 1,
                    borderSkipped: false,
                    borderRadius: 0,
                    barPercentage: 1.0,
                    categoryPercentage: 0.8,
                    base: currentPosition,
                    stack: 'timeline',
                    stageData: {
                        duration: time,
                        percentage: percentage,
                        startTime: currentPosition,
                        endTime: currentPosition + time
                    }
                });
                
                // To draw stage labels above the timeline
                const stagePosition = currentPosition + (time / 2);
                stagePlugins.push({
                    id: `stageLabel-${stage.metricKey}`,
                    afterDraw: (chart) => {
                        const ctx = chart.ctx;
                        const xAxis = chart.scales.x;
                        const yAxis = chart.scales.y;
                        
                        if (time / totalTime > 0.05) {
                            ctx.save();
                            ctx.fillStyle = '#495057';
                            ctx.font = '11px "Inter", sans-serif';
                            ctx.textAlign = 'center';
                            ctx.fillText(
                                stage.name, 
                                xAxis.getPixelForValue(stagePosition),
                                yAxis.getPixelForValue(0) - 15
                            );
                            ctx.restore();
                        }
                    }
                });
                
                // Update position for next stage
                currentPosition += time;
            }
        }
        
        // Update chart data with animation
        ganttChart.data.datasets = datasets;
        ganttChart.config.plugins = stagePlugins;
        ganttChart.options.scales.x.max = Math.max(totalTime * 1.05, 100);
        ganttChart.update({
            duration: 800,
            easing: 'easeOutQuart'
        });
        
        // Animate the canvas
        animateElement(ganttChartCanvas);
    }

    // Clean up resources when page is unloaded
    window.addEventListener('beforeunload', function() {
        if (ganttChart) {
            ganttChart.destroy();
            ganttChart = null;
        }
        
        if (chartResizeObserver) {
            chartResizeObserver.disconnect();
            chartResizeObserver = null;
        }
        
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    });

    // Update the customTooltip to use more efficient DOM operations
    function customTooltip(context) {
        // Tooltip element
        let tooltipEl = document.getElementById('chartjs-tooltip');

        // Create element on first render
        if (!tooltipEl) {
            tooltipEl = document.createElement('div');
            tooltipEl.id = 'chartjs-tooltip';
            tooltipEl.classList.add('chartjs-tooltip');
            document.body.appendChild(tooltipEl);
        }

        // Hide if no tooltip
        const tooltipModel = context.tooltip;
        if (tooltipModel.opacity === 0) {
            tooltipEl.style.opacity = '0';
            return;
        }

        // Set caret position
        tooltipEl.className = 'chartjs-tooltip';
        if (tooltipModel.yAlign) {
            tooltipEl.classList.add(tooltipModel.yAlign);
        } else {
            tooltipEl.classList.add('no-transform');
        }

        // Set content
        if (tooltipModel.body) {
            const dataPoint = tooltipModel.dataPoints[0];
            const dataset = context.chart.data.datasets[dataPoint.datasetIndex];
            const stageData = dataset.stageData || {};
            
            const title = dataset.label || 'Unknown Stage';
            const duration = stageData.duration ? `${stageData.duration.toFixed(1)} ms` : 'N/A';
            const percentage = stageData.percentage ? `${stageData.percentage.toFixed(1)}%` : 'N/A';
            const startTime = stageData.startTime ? `${stageData.startTime.toFixed(1)} ms` : 'N/A';
            const endTime = stageData.endTime ? `${stageData.endTime.toFixed(1)} ms` : 'N/A';

            tooltipEl.innerHTML = `
                <div class="tooltip-title">${title}</div>
                <div class="tooltip-body">
                    <div class="tooltip-metric">
                        <span class="tooltip-label">Duration:</span>
                        <span class="tooltip-value">${duration}</span>
                    </div>
                    <div class="tooltip-metric">
                        <span class="tooltip-label">Percentage:</span>
                        <span class="tooltip-value">${percentage}</span>
                    </div>
                    <div class="tooltip-metric">
                        <span class="tooltip-label">Start:</span>
                        <span class="tooltip-value">${startTime}</span>
                    </div>
                    <div class="tooltip-metric">
                        <span class="tooltip-label">End:</span>
                        <span class="tooltip-value">${endTime}</span>
                    </div>
                </div>
            `;
        }

        // Position tooltip
        const position = context.chart.canvas.getBoundingClientRect();
        
        // Set display, position, and z-index
        Object.assign(tooltipEl.style, {
            opacity: '1',
            position: 'absolute',
            left: position.left + window.pageXOffset + tooltipModel.caretX + 'px',
            top: position.top + window.pageYOffset + tooltipModel.caretY + 'px',
            zIndex: '1070',
            pointerEvents: 'none'
        });
    }

    // Event listener for toggling response view
    toggleResponseBtn.addEventListener('click', toggleResponseExpansion);

    // Add a function to restore UI state when reconnecting
    async function restoreUIState() {
        // If we have current query info, redisplay it
        if (currentQueryInfo) {
            displayActiveQuery(currentQueryInfo.query, currentQueryInfo.pipelineType);
        }
    }

    // Add this function to help debug event issues
    function logEventDetails(eventName, data) {
        console.log(`Event ${eventName} received:`, data);
        
        // For new_query events, let's do extra validation
        if (eventName === 'new_query') {
            console.log('Query content:', data.query ? 'Present' : 'Missing');
            console.log('Pipeline type:', data.pipeline_type ? 'Present' : 'Missing');
        }
        
        // For complete events, check if we have the same query info
        if (eventName === 'complete') {
            console.log('Complete event includes query:', data.query ? 'Yes' : 'No');
            console.log('Complete event includes pipeline type:', data.pipeline_type ? 'Yes' : 'No');
        }
    }

    // Connect to event stream on page load
    connectToEventStream();
    
    // Initialize the Gantt chart when the page loads
    initGanttChart();
    
    // Verify all required elements are present
    console.log('DOM loaded, checking elements:');
    console.log('- activeQueryElement:', !!activeQueryElement);
    console.log('- pipelineTypeLabel:', !!pipelineTypeLabel);
    console.log('- queryTimestamp:', !!queryTimestamp);
    
    // If any element is missing, log an error
    if (!activeQueryElement || !pipelineTypeLabel || !queryTimestamp) {
        console.error('Missing required DOM elements for query display');
    }
});

// Let's also add a manual recovery function we can call from the console if needed
window.forceUpdateQuery = function(query, pipelineType) {
    if (!query) {
        console.error('Cannot update with empty query');
        return;
    }
    
    currentQueryInfo = {
        query: query,
        pipelineType: pipelineType || 'unknown',
        timestamp: new Date()
    };
    
    displayActiveQuery(query, pipelineType);
    console.log('Query display manually updated');
};

// Add these utility functions to make animations and transitions smoother

// Function to add smooth entry animation to elements
function animateElement(element, delay = 0) {
    if (!element) return;
    
    element.style.opacity = '0';
    element.style.transform = 'translateY(10px)';
    element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    
    setTimeout(() => {
        element.style.opacity = '1';
        element.style.transform = 'translateY(0)';
    }, delay);
}

// Function to create a ripple effect on pipeline steps
function createRippleEffect(element) {
    if (!element) return;
    
    const ripple = document.createElement('span');
    ripple.classList.add('ripple');
    element.appendChild(ripple);
    
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${rect.width / 2 - size / 2}px`;
    ripple.style.top = `${rect.height / 2 - size / 2}px`;
    
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

// Initialize the page with animations
document.addEventListener('DOMContentLoaded', function() {
    // Add staggered animations to main UI sections
    const sections = document.querySelectorAll('.content-section');
    sections.forEach((section, index) => {
        animateElement(section, 100 + (index * 100));
    });
    
    // Animate the sidebar
    animateElement(document.querySelector('.sidebar'), 50);
    
    // Set initial button state
    toggleResponseBtn.style.display = 'none';
    
    // Initialize the chart
    initGanttChart();
    
    // Handle window resize events for truncation check
    window.addEventListener('resize', debounce(checkForTruncation, 100));
});