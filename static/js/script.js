function updateClock(){

const now=new Date();

document.getElementById("clock").innerHTML=
now.toLocaleDateString()+" | "+now.toLocaleTimeString();

}

setInterval(updateClock,1000);

updateClock();