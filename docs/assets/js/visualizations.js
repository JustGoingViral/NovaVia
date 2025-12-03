/**
 * NOVA ViA Interactive Visualizations
 * Demonstrates device orchestration, AI agent coordination, and HNK pharmacodynamics
 */

// ============================================================================
// Device Orchestration Visualization
// ============================================================================

class DeviceOrchestrationDemo {
    constructor() {
        this.devices = {
            hyperbaric: { pressure: 1.0, o2: 21, status: 'idle' },
            redlight: { wavelength: 660, intensity: 0, status: 'idle' },
            pemf: { freq: 0, intensity: 0, status: 'idle' },
            frequency: { binaural: 0, volume: 0, status: 'idle' }
        };
        this.isRunning = false;
        this.currentPhase = 'idle';
        this.timingAccuracies = [];
        this.chart = null;
        this.initChart();
        this.bindEvents();
    }

    initChart() {
        const ctx = document.getElementById('device-timeline-chart');
        if (!ctx) return;

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Hyperbaric (ATA)',
                        data: [],
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Red Light (%)',
                        data: [],
                        borderColor: '#f97316',
                        backgroundColor: 'rgba(249, 115, 22, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'PEMF (%)',
                        data: [],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Frequency (Hz)',
                        data: [],
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'Device Synchronization Timeline'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Intensity / Level'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time (seconds)'
                        }
                    }
                }
            }
        });
    }

    bindEvents() {
        const startBtn = document.getElementById('start-demo');
        const resetBtn = document.getElementById('reset-demo');

        if (startBtn) {
            startBtn.addEventListener('click', () => this.startDemo());
        }
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetDemo());
        }
    }

    async startDemo() {
        if (this.isRunning) return;
        this.isRunning = true;
        this.timingAccuracies = [];

        const phases = [
            { name: 'Preparation', duration: 2000, devices: { hyperbaric: { pressure: 1.0, o2: 21 } } },
            { name: 'Ramp Up', duration: 3000, devices: {
                hyperbaric: { pressure: 1.3, o2: 50 },
                redlight: { intensity: 30 },
                pemf: { freq: 10, intensity: 25 },
                frequency: { binaural: 10, volume: 15 }
            }},
            { name: 'Neuroplasticity Window', duration: 5000, devices: {
                hyperbaric: { pressure: 1.3, o2: 100 },
                redlight: { intensity: 70 },
                pemf: { freq: 10, intensity: 50 },
                frequency: { binaural: 10, volume: 25 }
            }},
            { name: 'Ramp Down', duration: 3000, devices: {
                hyperbaric: { pressure: 1.0, o2: 50 },
                redlight: { intensity: 15 },
                pemf: { freq: 5, intensity: 10 },
                frequency: { binaural: 5, volume: 10 }
            }},
            { name: 'Recovery', duration: 2000, devices: {
                hyperbaric: { pressure: 1.0, o2: 21 },
                redlight: { intensity: 0 },
                pemf: { freq: 0, intensity: 0 },
                frequency: { binaural: 0, volume: 0 }
            }}
        ];

        let time = 0;
        for (const phase of phases) {
            this.updatePhase(phase.name);
            await this.executePhase(phase, time);
            time += phase.duration / 1000;
        }

        this.updatePhase('Complete');
        this.isRunning = false;
    }

    async executePhase(phase, startTime) {
        const targetTime = performance.now();
        const steps = 10;
        const stepDuration = phase.duration / steps;

        for (let i = 0; i <= steps; i++) {
            await this.delay(stepDuration);
            
            // Calculate timing accuracy
            const actualTime = performance.now();
            const expectedTime = targetTime + (i * stepDuration);
            const accuracy = Math.abs(actualTime - expectedTime);
            this.timingAccuracies.push(accuracy);
            
            // Update timing display
            const avgAccuracy = this.timingAccuracies.reduce((a, b) => a + b, 0) / this.timingAccuracies.length;
            document.getElementById('timing-accuracy').textContent = avgAccuracy.toFixed(3);

            // Interpolate device values
            const progress = i / steps;
            this.interpolateDevices(phase.devices, progress);
            this.updateDeviceDisplay();
            this.updateChart(startTime + (i * stepDuration / 1000));
        }
    }

    interpolateDevices(targetDevices, progress) {
        for (const [device, params] of Object.entries(targetDevices)) {
            for (const [param, target] of Object.entries(params)) {
                const current = this.devices[device][param] || 0;
                this.devices[device][param] = current + (target - current) * progress;
            }
            this.devices[device].status = 'active';
        }
    }

    updateDeviceDisplay() {
        // Hyperbaric
        document.getElementById('hyperbaric-pressure').textContent = this.devices.hyperbaric.pressure.toFixed(1);
        document.getElementById('hyperbaric-o2').textContent = Math.round(this.devices.hyperbaric.o2);
        this.updateCardStatus('hyperbaric-card', this.devices.hyperbaric.pressure > 1.0);

        // Red Light
        document.getElementById('redlight-wavelength').textContent = this.devices.redlight.wavelength;
        document.getElementById('redlight-intensity').textContent = Math.round(this.devices.redlight.intensity);
        this.updateCardStatus('redlight-card', this.devices.redlight.intensity > 0);

        // PEMF
        document.getElementById('pemf-freq').textContent = Math.round(this.devices.pemf.freq);
        document.getElementById('pemf-intensity').textContent = Math.round(this.devices.pemf.intensity);
        this.updateCardStatus('pemf-card', this.devices.pemf.intensity > 0);

        // Frequency
        document.getElementById('freq-binaural').textContent = Math.round(this.devices.frequency.binaural);
        document.getElementById('freq-volume').textContent = Math.round(this.devices.frequency.volume);
        this.updateCardStatus('frequency-card', this.devices.frequency.volume > 0);
    }

    updateCardStatus(cardId, isActive) {
        const card = document.getElementById(cardId);
        if (!card) return;

        if (isActive) {
            card.classList.add('active');
            card.querySelector('.device-status').textContent = 'Active';
            card.querySelector('.device-status').className = 'device-status status-active';
        } else {
            card.classList.remove('active');
            card.querySelector('.device-status').textContent = 'Idle';
            card.querySelector('.device-status').className = 'device-status status-idle';
        }
    }

    updateChart(time) {
        if (!this.chart) return;

        this.chart.data.labels.push(time.toFixed(1));
        this.chart.data.datasets[0].data.push(this.devices.hyperbaric.pressure * 50);
        this.chart.data.datasets[1].data.push(this.devices.redlight.intensity);
        this.chart.data.datasets[2].data.push(this.devices.pemf.intensity);
        this.chart.data.datasets[3].data.push(this.devices.frequency.binaural);
        this.chart.update('none');
    }

    updatePhase(phaseName) {
        document.getElementById('current-phase').textContent = phaseName;
    }

    resetDemo() {
        this.isRunning = false;
        this.devices = {
            hyperbaric: { pressure: 1.0, o2: 21, status: 'idle' },
            redlight: { wavelength: 660, intensity: 0, status: 'idle' },
            pemf: { freq: 0, intensity: 0, status: 'idle' },
            frequency: { binaural: 0, volume: 0, status: 'idle' }
        };
        this.updateDeviceDisplay();
        this.updatePhase('Idle');
        document.getElementById('timing-accuracy').textContent = '0.000';

        if (this.chart) {
            this.chart.data.labels = [];
            this.chart.data.datasets.forEach(ds => ds.data = []);
            this.chart.update();
        }

        // Reset card status
        ['hyperbaric-card', 'redlight-card', 'pemf-card', 'frequency-card'].forEach(id => {
            this.updateCardStatus(id, false);
        });
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// ============================================================================
// AI Agent Network Visualization (D3.js)
// ============================================================================

class AgentNetworkVisualization {
    constructor() {
        this.svg = null;
        this.simulation = null;
        this.init();
    }

    init() {
        const container = document.getElementById('agent-network-svg');
        if (!container) return;

        const width = container.clientWidth || 800;
        const height = 500;

        // Define nodes (agents)
        const nodes = [
            { id: 'orchestrator', name: 'Master Orchestrator', icon: '🎼', type: 'master', x: width/2, y: height/2 },
            { id: 'crisis', name: 'Crisis Intervention', icon: '🚨', type: 'agent', x: width/4, y: height/4 },
            { id: 'medication', name: 'Medication', icon: '💊', type: 'agent', x: 3*width/4, y: height/4 },
            { id: 'biohacking', name: 'Biohacking', icon: '🔧', type: 'agent', x: width/4, y: 3*height/4 },
            { id: 'therapy', name: 'Therapy', icon: '🧘', type: 'agent', x: 3*width/4, y: 3*height/4 },
            { id: 'analytics', name: 'Analytics', icon: '📊', type: 'agent', x: width/2, y: height/6 }
        ];

        // Define links (connections)
        const links = [
            { source: 'orchestrator', target: 'crisis', type: 'bidirectional' },
            { source: 'orchestrator', target: 'medication', type: 'bidirectional' },
            { source: 'orchestrator', target: 'biohacking', type: 'bidirectional' },
            { source: 'orchestrator', target: 'therapy', type: 'bidirectional' },
            { source: 'orchestrator', target: 'analytics', type: 'bidirectional' },
            { source: 'crisis', target: 'medication', type: 'data' },
            { source: 'biohacking', target: 'therapy', type: 'data' },
            { source: 'analytics', target: 'medication', type: 'data' },
            { source: 'analytics', target: 'therapy', type: 'data' }
        ];

        // Create SVG
        this.svg = d3.select('#agent-network-svg')
            .attr('width', width)
            .attr('height', height);

        // Add gradient for links
        const defs = this.svg.append('defs');
        const gradient = defs.append('linearGradient')
            .attr('id', 'link-gradient')
            .attr('gradientUnits', 'userSpaceOnUse');
        gradient.append('stop').attr('offset', '0%').attr('stop-color', '#4f46e5');
        gradient.append('stop').attr('offset', '100%').attr('stop-color', '#06b6d4');

        // Create force simulation
        this.simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(150))
            .force('charge', d3.forceManyBody().strength(-500))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(60));

        // Draw links
        const link = this.svg.append('g')
            .selectAll('line')
            .data(links)
            .enter()
            .append('line')
            .attr('stroke', d => d.type === 'bidirectional' ? '#4f46e5' : '#94a3b8')
            .attr('stroke-width', d => d.type === 'bidirectional' ? 3 : 1.5)
            .attr('stroke-dasharray', d => d.type === 'data' ? '5,5' : 'none')
            .attr('opacity', 0.7);

        // Draw nodes
        const node = this.svg.append('g')
            .selectAll('g')
            .data(nodes)
            .enter()
            .append('g')
            .attr('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (event, d) => this.dragStarted(event, d))
                .on('drag', (event, d) => this.dragged(event, d))
                .on('end', (event, d) => this.dragEnded(event, d)));

        // Node circles
        node.append('circle')
            .attr('r', d => d.type === 'master' ? 50 : 35)
            .attr('fill', d => d.type === 'master' ? '#4f46e5' : '#f8fafc')
            .attr('stroke', d => d.type === 'master' ? '#3730a3' : '#4f46e5')
            .attr('stroke-width', 3);

        // Node icons
        node.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', d => d.type === 'master' ? 8 : 5)
            .attr('font-size', d => d.type === 'master' ? 28 : 22)
            .text(d => d.icon);

        // Node labels
        node.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', d => d.type === 'master' ? 75 : 55)
            .attr('font-size', 12)
            .attr('font-weight', 500)
            .attr('fill', '#374151')
            .text(d => d.name);

        // Simulation tick
        this.simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node.attr('transform', d => `translate(${d.x}, ${d.y})`);
        });

        // Animate data flow
        this.animateDataFlow();
    }

    dragStarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragEnded(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    animateDataFlow() {
        // Periodically highlight communication between agents
        this.animationIntervalId = setInterval(() => {
            const lines = this.svg.selectAll('line');
            lines.transition()
                .duration(500)
                .attr('stroke-width', function() {
                    return Math.random() > 0.5 ? 5 : d3.select(this).attr('stroke-width');
                })
                .transition()
                .duration(500)
                .attr('stroke-width', function(d) {
                    return d.type === 'bidirectional' ? 3 : 1.5;
                });
        }, 2000);
    }

    destroy() {
        // Clean up interval to prevent memory leaks
        if (this.animationIntervalId) {
            clearInterval(this.animationIntervalId);
        }
        if (this.simulation) {
            this.simulation.stop();
        }
    }
}

// ============================================================================
// HNK Pharmacodynamics Visualization
// ============================================================================

// HNK Model Constants
const HNK_CONSTANTS = {
    BDNF_MAX_INCREASE: 2.5,
    EC50_SQUARED: 0.04,  // Math.pow(0.2, 2) pre-calculated
    MOOD_SCALE_FACTOR: 0.4,
    MOOD_BASE_OFFSET: 0.3,
    DISSOCIATION_BASE_RISK: 0.05,
    MAX_SAFE_DOSE: 0.5
};

class HNKVisualization {
    constructor() {
        this.doseResponseChart = null;
        this.bdnfDynamicsChart = null;
        this.initCharts();
        this.bindControls();
    }

    initCharts() {
        this.initDoseResponseChart();
        this.initBDNFDynamicsChart();
    }

    initDoseResponseChart() {
        const ctx = document.getElementById('dose-response-chart');
        if (!ctx) return;

        // Generate dose-response data
        const doses = [];
        const bdnfResponse = [];
        const moodResponse = [];
        const dissociationRisk = [];

        for (let dose = 0.05; dose <= 0.5; dose += 0.01) {
            doses.push(dose.toFixed(2));
            
            // BDNF response (Hill equation simulation)
            const dosePowerTwo = dose * dose;
            const bdnf = 1 + HNK_CONSTANTS.BDNF_MAX_INCREASE * dosePowerTwo / (HNK_CONSTANTS.EC50_SQUARED + dosePowerTwo);
            bdnfResponse.push(bdnf);
            
            // Mood improvement
            const mood = Math.min(1.0, (bdnf - 1) * HNK_CONSTANTS.MOOD_SCALE_FACTOR + HNK_CONSTANTS.MOOD_BASE_OFFSET);
            moodResponse.push(mood);
            
            // Dissociation risk (very low for HNK)
            const dissociation = HNK_CONSTANTS.DISSOCIATION_BASE_RISK * (1 + dose / HNK_CONSTANTS.MAX_SAFE_DOSE * 0.5);
            dissociationRisk.push(dissociation);
        }

        this.doseResponseChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: doses,
                datasets: [
                    {
                        label: 'BDNF Fold Increase',
                        data: bdnfResponse,
                        borderColor: '#4f46e5',
                        backgroundColor: 'rgba(79, 70, 229, 0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Mood Improvement Score',
                        data: moodResponse,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Dissociation Risk',
                        data: dissociationRisk,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'HNK Dose-Response Relationships'
                    },
                    annotation: {
                        annotations: {
                            optimalDose: {
                                type: 'line',
                                xMin: 25,
                                xMax: 25,
                                borderColor: '#f59e0b',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    display: true,
                                    content: 'Optimal (0.3 mg/kg)'
                                }
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Response'
                        },
                        min: 0,
                        max: 4
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Risk'
                        },
                        min: 0,
                        max: 0.2,
                        grid: {
                            drawOnChartArea: false
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'HNK Dose (mg/kg)'
                        }
                    }
                }
            }
        });
    }

    initBDNFDynamicsChart() {
        const ctx = document.getElementById('bdnf-dynamics-chart');
        if (!ctx) return;

        // Generate BDNF dynamics over 48 hours
        const times = [];
        const bdnfLevels = [];
        const hnkConcentration = [];
        const baseline = 15; // ng/mL

        for (let t = 0; t <= 48; t += 0.5) {
            times.push(t);
            
            // HNK concentration (exponential decay, half-life ~2 hours)
            const hnk = 0.3 * Math.exp(-0.35 * t);
            hnkConcentration.push(hnk * 100); // Scale for visibility
            
            // BDNF dynamics (delayed response, peak at 4-6 hours)
            const bdnf = baseline * (1 + 1.5 * (1 - Math.exp(-0.5 * t)) * Math.exp(-0.03 * t));
            bdnfLevels.push(bdnf);
        }

        this.bdnfDynamicsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: times,
                datasets: [
                    {
                        label: 'BDNF (ng/mL)',
                        data: bdnfLevels,
                        borderColor: '#4f46e5',
                        backgroundColor: 'rgba(79, 70, 229, 0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'HNK Concentration (scaled)',
                        data: hnkConcentration,
                        borderColor: '#f97316',
                        backgroundColor: 'rgba(249, 115, 22, 0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'BDNF Dynamics Following HNK Infusion'
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: 'BDNF (ng/mL)'
                        },
                        min: 10,
                        max: 40
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'HNK Concentration'
                        },
                        min: 0,
                        max: 35,
                        grid: {
                            drawOnChartArea: false
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time (hours)'
                        }
                    }
                }
            }
        });
    }

    bindControls() {
        // Weight slider
        const weightSlider = document.getElementById('patient-weight');
        const weightValue = document.getElementById('patient-weight-value');
        if (weightSlider) {
            weightSlider.addEventListener('input', () => {
                weightValue.textContent = weightSlider.value;
                this.updateSimulation();
            });
        }

        // Dose slider
        const doseSlider = document.getElementById('hnk-dose');
        const doseValue = document.getElementById('hnk-dose-value');
        if (doseSlider) {
            doseSlider.addEventListener('input', () => {
                doseValue.textContent = parseFloat(doseSlider.value).toFixed(2);
                this.updateSimulation();
            });
        }

        // Metabolism profile
        const metabolismSelect = document.getElementById('metabolism-profile');
        if (metabolismSelect) {
            metabolismSelect.addEventListener('change', () => this.updateSimulation());
        }

        // Hormonal phase
        const hormonalSelect = document.getElementById('hormonal-phase');
        if (hormonalSelect) {
            hormonalSelect.addEventListener('change', () => this.updateSimulation());
        }
    }

    updateSimulation() {
        const weight = parseFloat(document.getElementById('patient-weight')?.value || 70);
        const dose = parseFloat(document.getElementById('hnk-dose')?.value || 0.3);
        const metabolism = document.getElementById('metabolism-profile')?.value || 'normal';
        const hormonal = document.getElementById('hormonal-phase')?.value || 'na';

        // Get metabolism factor
        const metabolismFactors = { slow: 0.6, normal: 1.0, rapid: 1.4, ultra_rapid: 1.8 };
        const metabFactor = metabolismFactors[metabolism] || 1.0;

        // Get hormonal efficacy modifier
        const hormonalModifiers = {
            na: 1.0,
            follicular: 1.2,
            ovulatory: 1.25,
            luteal: 0.95,
            postpartum: 0.75
        };
        const hormModifier = hormonalModifiers[hormonal] || 1.0;

        // Calculate predictions using constants
        const adjustedDose = dose * metabFactor;
        const adjustedDosePowerTwo = adjustedDose * adjustedDose;
        const bdnfIncrease = 1 + HNK_CONSTANTS.BDNF_MAX_INCREASE * adjustedDosePowerTwo / (HNK_CONSTANTS.EC50_SQUARED + adjustedDosePowerTwo);
        const adjustedBdnf = bdnfIncrease * hormModifier;
        const moodScore = Math.min(1.0, (adjustedBdnf - 1) * HNK_CONSTANTS.MOOD_SCALE_FACTOR + HNK_CONSTANTS.MOOD_BASE_OFFSET);
        const dissociationRisk = HNK_CONSTANTS.DISSOCIATION_BASE_RISK * (1 + dose / HNK_CONSTANTS.MAX_SAFE_DOSE * 0.5);

        // Update display
        document.getElementById('predicted-bdnf').textContent = adjustedBdnf.toFixed(1) + 'x';
        document.getElementById('mood-score').textContent = moodScore.toFixed(2);
        document.getElementById('dissociation-risk').textContent = (dissociationRisk * 100).toFixed(0) + '%';
        document.getElementById('efficacy-modifier').textContent = hormModifier.toFixed(2) + 'x';

        // Update risk styling
        const riskElement = document.getElementById('dissociation-risk');
        if (dissociationRisk < 0.08) {
            riskElement.className = 'result-value low-risk';
        } else {
            riskElement.className = 'result-value high-risk';
        }
    }
}

// ============================================================================
// EEG Visualization
// ============================================================================

class EEGVisualization {
    constructor() {
        this.chart = null;
        this.data = [];
        this.isRunning = true;
        this.init();
    }

    init() {
        const ctx = document.getElementById('eeg-chart');
        if (!ctx) return;

        // Initialize with random EEG-like data
        const labels = [];
        const alphaData = [];
        const thetaData = [];
        const gammaData = [];

        for (let i = 0; i < 100; i++) {
            labels.push(i);
            alphaData.push(this.generateEEGPoint(0.75, 0.2));
            thetaData.push(this.generateEEGPoint(0.45, 0.15));
            gammaData.push(this.generateEEGPoint(0.32, 0.1));
        }

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Alpha (8-12 Hz)',
                        data: alphaData,
                        borderColor: '#818cf8',
                        backgroundColor: 'transparent',
                        tension: 0.2,
                        pointRadius: 0
                    },
                    {
                        label: 'Theta (4-8 Hz)',
                        data: thetaData,
                        borderColor: '#34d399',
                        backgroundColor: 'transparent',
                        tension: 0.2,
                        pointRadius: 0
                    },
                    {
                        label: 'Gamma (30-100 Hz)',
                        data: gammaData,
                        borderColor: '#fbbf24',
                        backgroundColor: 'transparent',
                        tension: 0.2,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Real-time EEG Power Spectrum'
                    },
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 1.5,
                        title: {
                            display: true,
                            text: 'Power (normalized)'
                        }
                    },
                    x: {
                        display: false
                    }
                }
            }
        });

        // Start real-time update
        this.startRealTimeUpdate();
    }

    generateEEGPoint(mean, variance) {
        // Generate realistic EEG-like fluctuations
        return mean + (Math.random() - 0.5) * variance * 2;
    }

    startRealTimeUpdate() {
        this.updateIntervalId = setInterval(() => {
            if (!this.isRunning || !this.chart) return;

            // Shift data and add new points
            this.chart.data.datasets.forEach((dataset, index) => {
                dataset.data.shift();
                const means = [0.75, 0.45, 0.32];
                const variances = [0.2, 0.15, 0.1];
                dataset.data.push(this.generateEEGPoint(means[index], variances[index]));
            });

            this.chart.update('none');

            // Update indicators
            this.updateIndicators();
        }, 100);
    }

    stop() {
        this.isRunning = false;
        if (this.updateIntervalId) {
            clearInterval(this.updateIntervalId);
        }
    }

    destroy() {
        // Clean up interval to prevent memory leaks
        this.stop();
        if (this.chart) {
            this.chart.destroy();
        }
    }

    updateIndicators() {
        // Calculate current power values
        const alpha = 0.75 + (Math.random() - 0.5) * 0.1;
        const theta = 0.45 + (Math.random() - 0.5) * 0.08;
        const gamma = 0.32 + (Math.random() - 0.5) * 0.06;
        const coherence = 0.68 + (Math.random() - 0.5) * 0.1;

        // Update bars
        document.getElementById('alpha-power').style.width = (alpha * 100) + '%';
        document.getElementById('theta-power').style.width = (theta * 100) + '%';
        document.getElementById('gamma-power').style.width = (gamma * 100) + '%';
        document.getElementById('coherence-power').style.width = (coherence * 100) + '%';

        // Update values
        document.getElementById('alpha-value').textContent = alpha.toFixed(2);
        document.getElementById('theta-value').textContent = theta.toFixed(2);
        document.getElementById('gamma-value').textContent = gamma.toFixed(2);
        document.getElementById('coherence-value').textContent = coherence.toFixed(2);

        // Update window prediction
        const confidence = 80 + Math.random() * 15;
        const timeToWindow = 2 + Math.random() * 4;
        document.getElementById('window-confidence').textContent = confidence.toFixed(0) + '%';
        document.getElementById('window-time').textContent = timeToWindow.toFixed(1);
    }
}

// ============================================================================
// Initialize All Visualizations
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize all visualization components
    window.deviceDemo = new DeviceOrchestrationDemo();
    window.agentNetwork = new AgentNetworkVisualization();
    window.hnkViz = new HNKVisualization();
    window.eegViz = new EEGVisualization();

    // Initial simulation update
    window.hnkViz.updateSimulation();

    console.log('🌟 NOVA ViA Visualizations initialized');
});

// Smooth scrolling for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});
