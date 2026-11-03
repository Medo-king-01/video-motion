import {compileNestedSequence} from './lib/motion-plan.js';
import {compileSvgMorph} from './lib/svg-morph.js';
import {FROM,TO} from './morph-plans.js';
export const DIRECTION={scenes:[{scene:1,textStyles:{label:'softfade'},fontStyles:{label:{family:'Cairo',weight:800}}}]};
export const SPEC={version:1,items:[{id:'group',at:.2,timeScale:0.8,sequence:{version:1,markers:{go:.1},items:[
  {id:'shape',at:'go',sequence:{version:1,items:[{id:'progress',track:'value',at:0,duration:1.5,from:0,to:1,easing:'cubicInOut'}]}},
  {id:'finish',track:'accent',at:'>',duration:.3,from:0,to:1}]}}]};
const sequence=compileNestedSequence(SPEC),morph=compileSvgMorph({version:1,from:FROM,to:TO,count:32});
export function frameAt(t){const values=sequence.at(t);return {art:morph.at(values['group/shape/value']),values};}
