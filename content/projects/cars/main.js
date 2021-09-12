const Chart = require("chart.js")

data = JSON.parse(cars)

const ctx = document.getElementById("price-by-year");

const myChart = new Chart(ctx, {
    type: 'scatter',
    data: {datasets: [{
        data: data,
        parsing: {
            xAxisKey: 'year',
            yAxisKey: 'price'
        }}]
    },
    options: {
        plugins: {
            title: {
                display: true,
                text: "Price of listing by year of car",
            },
            legend: { display: false }
        },
        scales: {
            xAxis: {
                min: 1990,
                max: 2025,
                title: {
                    display: true,
                    text: "Year of car"
                }
            },
            yAxis: {
                title: {
                    display: true,
                    text: "Price of car"
                }
            }
        }
    }
});

