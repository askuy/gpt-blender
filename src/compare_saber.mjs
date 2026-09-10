// Local visual study; reference photography stays in the ignored cache.
// These are aligned crops, not a machine-generated identity or likeness score.
import sharp from 'sharp';
import { mkdir, access } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root=fileURLToPath(new URL('../',import.meta.url));
const cache=join(root,'.cache/saber-reference');
await mkdir(cache,{recursive:true});
const panels=[
  {file:join(cache,'figure-5.jpg'),crop:{left:222,top:135,width:169,height:180},title:'REFERENCE / GOOD SMILE',note:'Saber ~Triumphant Excalibur~ · Product 2780'},
  {file:join(cache,'v2/face.png'),crop:{left:216,top:313,width:572,height:573},title:'BEFORE / V2',note:'Long lower face · small irises · even fringe'},
  {file:join(root,'renders/saber/face.png'),crop:{left:211,top:312,width:585,height:559},title:'CURRENT / V3',note:'Shorter jaw · fuller teal eyes · swept layers'},
];
const width=440,height=500,gap=18,pad=24;
const composites=[];
for(let i=0;i<panels.length;i++){
  const p=panels[i];await access(p.file);
  composites.push({input:await sharp(p.file).extract(p.crop).resize(width,height,{fit:'contain',background:'#e8e4dd'}).toBuffer(),left:pad+i*(width+gap),top:106});
}
const text=Buffer.from(`<svg width="1404" height="728" xmlns="http://www.w3.org/2000/svg"><style>text{font-family:Arial,sans-serif;fill:#303630}.title{font-size:23px;font-weight:bold}.label{font-size:15px;font-weight:bold}.note{font-size:12px;fill:#62665f}</style><text x="24" y="40" class="title">SABER / REFERENCE &amp; PORTRAIT STUDY</text>${panels.map((p,i)=>`<text x="${pad+i*(width+gap)}" y="84" class="label">${p.title}</text><text x="${pad+i*(width+gap)}" y="633" class="note">${p.note}</text>`).join('')}<text x="24" y="679" class="note">Crops aligned to the head silhouette. Pose, expression and lighting differ; this is not an identity percentage.</text><text x="24" y="702" class="note">Reference: goodsmile.info/en/product/2780/ · Photography belongs to its rights holders. Local study only.</text></svg>`);
composites.push({input:text,left:0,top:0});
await sharp({create:{width:1404,height:728,channels:3,background:'#f5f2eb'}}).composite(composites).jpeg({quality:94}).toFile(join(cache,'likeness-comparison.jpg'));
console.log(join(cache,'likeness-comparison.jpg'));
