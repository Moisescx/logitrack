document.addEventListener("DOMContentLoaded", function () {
    console.log('DOM loaded, initializing charts...');
    
    // 📊 Camiones
    const truckStatusCtx = document.getElementById('truckStatusChart');
    if (truckStatusCtx) {
        console.log('Truck chart element found');
        console.log('Truck labels:', window.truckStatusLabels);
        console.log('Truck values:', window.truckStatusValues);
        
        if (window.truckStatusLabels && window.truckStatusLabels.length > 0) {
            new Chart(truckStatusCtx, {
                type: 'doughnut',
                data: {
                    labels: window.truckStatusLabels,
                    datasets: [{
                        label: 'Camiones',
                        data: window.truckStatusValues,
                        backgroundColor: ['#3B82F6','#22C55E','#F59E0B','#EF4444']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        } else {
            console.warn('No hay datos para el gráfico de camiones');
            truckStatusCtx.innerHTML = '<p>No hay datos disponibles</p>';
        }
    } else {
        console.error('Elemento truckStatusChart no encontrado');
    }

    // 📊 Rutas
    const routeStatusCtx = document.getElementById('routeStatusChart');
    if (routeStatusCtx) {
        console.log('Route chart element found');
        console.log('Route labels:', window.routeStatusLabels);
        console.log('Route values:', window.routeStatusValues);
        
        if (window.routeStatusLabels && window.routeStatusLabels.length > 0) {
            new Chart(routeStatusCtx, {
                type: 'bar',
                data: {
                    labels: window.routeStatusLabels,
                    datasets: [{
                        label: 'Cantidad',
                        data: window.routeStatusValues,
                        backgroundColor: '#3B82F6'
                    }]
                },
                options: { 
                    responsive: true, 
                    scales: { 
                        y: { beginAtZero: true } 
                    } 
                }
            });
        } else {
            console.warn('No hay datos para el gráfico de rutas');
            routeStatusCtx.innerHTML = '<p>No hay datos disponibles</p>';
        }
    } else {
        console.error('Elemento routeStatusChart no encontrado');
    }
});